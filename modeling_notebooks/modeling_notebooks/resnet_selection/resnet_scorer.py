from pathlib import Path
from dataclasses import dataclass
from pprint import pprint
from itertools import batched
from typing import Iterable
from enum import Enum

from PIL import Image

import torch
import torchvision
from torchvision.io import read_image
from torchvision.transforms import ToPILImage
from torchvision.models.resnet import ResNet
from torchvision.models import WeightsEnum
from torchvision.models import resnet18, ResNet18_Weights
from torchvision.models import resnet34, ResNet34_Weights
from torchvision.models import resnet50, ResNet50_Weights
from torchvision.models import resnet101, ResNet101_Weights
from torchvision.models import resnet152, ResNet152_Weights

CPU_DEVICE = torch.device("cpu")


@dataclass(frozen=True)
class OtterPredictionResult:
    """
    Utility container for the predictions of a known otter image.
    """

    category: str
    category_score: float
    otter_score: float
    file_path: Path = None


class ResNetVersions(Enum):
    v18 = "ResNet-18"
    v34 = "ResNet-34"
    v50 = "ResNet-50"
    v101 = "ResNet-101"
    v152 = "ResNet-152"


class OtterScorer:
    def __init__(
        self,
        resnet_version: ResNetVersions = ResNetVersions.v50,
        device: torch.device = CPU_DEVICE,
    ) -> None:

        self.device = device

        # Select the model constructor and weights based on the requested version
        match resnet_version:
            case ResNetVersions.v18:
                model_constructor = resnet18
                model_weights = ResNet18_Weights.DEFAULT
            case ResNetVersions.v34:
                model_constructor = resnet34
                model_weights = ResNet34_Weights.DEFAULT
            case ResNetVersions.v50:
                model_constructor = resnet50
                model_weights = ResNet50_Weights.DEFAULT
            case ResNetVersions.v101:
                model_constructor = resnet101
                model_weights = ResNet101_Weights.DEFAULT
            case ResNetVersions.v152:
                model_constructor = resnet152
                model_weights = ResNet152_Weights.DEFAULT

        # Instantiate the model with default weights, move it to specified
        # compute device (hopefully a GPU) and set it to eval mode
        self.weights: WeightsEnum = model_weights
        self.model: ResNet = model_constructor(weights=self.weights)
        self.model.to(self.device)
        self.model.eval()

        # Store the preprocess transforms for later use
        self.preprocess = self.weights.transforms()

        # Look up the index of "otter" among the model's output classes
        self.categories: list[str] = self.weights.meta["categories"]
        self._otter_index = self.categories.index("otter")

    def preprocess_image(
        self, item: Image.Image | Path | str | OtterPredictionResult
    ) -> Image.Image:
        """
        Apply the model's preprocessing transforms to an image.

        This function is useful for diagnostics and interpretability. Typically the preprocessing
        transforms directly produce a tensor. But this function converts the tensor back to an image,
        also removing the scaling and normalization applied by the transforms in order to make the
        image more human-interpretable.

        :param item:  An image, a path to an image file, or an OtterPredictionResult object.
        :return:  The image after applying the preprocessing transforms.
        """
        match item:
            case Image.Image as image_class:
                img = image_class
            case str(s):
                img = read_image(Path(s).expanduser())
            case Path(p):
                img = read_image(p.expanduser())
            case OtterPredictionResult as pred:
                img = read_image(pred.file_path)

        # Apply the preprocessing transforms
        tensor = self.preprocess(img)

        # Undo the normalization and scaling transformations
        transform_means: list[float] = self.preprocess.mean
        transform_stdev: list[float] = self.preprocess.std
        for i in range(3):
            tensor[i] = tensor[i] * transform_stdev[i] + transform_means[i]

        tensor = torch.clip(tensor, 0, 1)

        # Convert the tensor back to an image
        return ToPILImage()(tensor)

    def score_image_at_path(self, path: Path | str) -> OtterPredictionResult:
        """
        Score the image located at the given filepath.

        Will raise a RuntimError if the image is not convertable to a tensor that
        can be scored by a ResNet model.

        :param path:  The path to the image file.
        :return:  An OtterPredictionResult object with the prediction results.
        """

        if isinstance(path, str):
            path = Path(path)

        # Obtain a prediction
        img = read_image(path.expanduser())
        batch = self.preprocess(img).unsqueeze(0).to(self.device)
        prediction = self.model(batch).squeeze(0).softmax(0)

        # Package and return results
        category_id = prediction.argmax().item()
        return OtterPredictionResult(
            category=self.categories[category_id],
            category_score=prediction[category_id].item(),
            otter_score=prediction[self._otter_index].item(),
            file_path=path,
        )

    def score_batch_of_images(
        self, image_files: Iterable[Path | str]
    ) -> list[OtterPredictionResult]:
        """
        Score a batch of images located at the given filepaths.

        Images will be processed in parallel on the GPU. The results will be returned as a list
        of OtterPredictionResult objects, one for each image in the batch.

        Images that cannot be converted to tensors will be skipped and a warning will be
        printed. This means that the length of the returned list may be less than the length
        of the input.

        :param image_files:  An iterable of paths to image files.
        :return:  A list of OtterPredictionResult objects with the prediction results.
        """
        # Load, transform, and stack image files together into a batch
        imgs = list()
        results_files = list()
        for file in image_files:
            try:
                img = read_image(file)
                img = self.preprocess(img)
            except:
                print(f"Warning: Could not process file {file} into an image tensor.")
                continue

            imgs.append(img)
            results_files.append(file)

        # Stop early if we don't have any images to score
        if not imgs:
            return []

        batch = torch.stack(imgs).to(self.device)

        # Run the batch through the model
        predictions = self.model(batch)
        probabilities = predictions.softmax(dim=1)

        # Package and return results
        results = list()
        for probability, file in zip(probabilities, results_files):
            category_id = probability.argmax().item()
            results.append(
                OtterPredictionResult(
                    category=self.categories[category_id],
                    category_score=probability[category_id].item(),
                    otter_score=probability[self._otter_index].item(),
                    file_path=file,
                )
            )

        return results

    def score_images_in_directory(
        self, directory: Path | str, batch_size: int = 64
    ) -> list[OtterPredictionResult]:
        """
        Score all images in a directory and return the results as a list.

        Scans the directory recursively for images and scores each one. Returns a list of
        OtterPredictionResult objects, one for each image found. This is more efficent than
        calling score_image_at_path() on each image individually, because if can process the
        images as a "batch" on the GPU.

        :param directory:  The path to the directory containing the images.
        :param batch_size:  The maximum number of images to process in a single batch.
        :return:  A list of OtterPredictionResult objects with the prediction results.
        """
        if isinstance(directory, str):
            directory = Path(directory)

        # Find all images in the directory
        image_files = (
            list(directory.rglob("*.jpg"))
            + list(directory.rglob("*.jpeg"))
            + list(directory.rglob("*.png"))
        )

        # Score the images in batches
        results = list()
        for batch_files in batched(image_files, batch_size):
            results.extend(self.score_batch_of_images(batch_files))

        return results
