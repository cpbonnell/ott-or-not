from metaflow import FlowSpec, step, pypi


class GpuCheckFlow(FlowSpec):

    @pypi(packages={"torch": "2.10.0"})
    @step
    def start(self):
        import torch

        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA device: {torch.cuda.get_device_name(0)}")
            x = torch.randn(3, 3, device="cuda")
            print(f"Tensor on GPU:\n{x}")
        else:
            print("No GPU detected — running on CPU only")
        self.next(self.end)

    @step
    def end(self):
        print("Done.")


if __name__ == "__main__":
    GpuCheckFlow()
