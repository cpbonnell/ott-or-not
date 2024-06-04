# Curator
An application for finding, acquiring, and managing collections of images for machine learning.

## Overview
Curator uses custom image search services to scan the internet for images based on search terms that are supplied by the user. The images are downloaded to an image repository, and metadata about those images (such as what search terms have yielded that image and user-specified tags about its content) is persisted as part of the image collection. All images are stored only once, even if the image is returned by multiple image sources or searches. The metadata is maintained and updated for each image across all searches that it appears in.

## Usage
The help text for the application will document all of the specific options and parameters for the application:
```bash
poetry run curator --help
```

Currently, Curator supports two methods of ingesting new images. If you already have a directory structure with images in it, vyou may import them to an existing repository by using the `import` sub-command. This utility will recursively crawl the specified directory and its sub-directories, and import all image files it finds there. You may optionally instruct the import utility to tag each image with the name of its parent directory. This is helpful for situations where you have an already organized collection of images for a Machine Learning project, since such collections typically organize images into sub-directories based on the images training label.
```bash
poetry run curator import /path/to/image/collection
```

The other method of acquiring new images is through a new image search. This sub-command requires a "shopping-list.yaml" file, which by default it will look for in the root of the directory where the images will be saved. This sub-comand will execute image searches using the specified image search service, and then download the returned image URLs in parallel. The downloaded images will be persisted to the image repository together with the relevant metadata.
```bash
poetry run curator search
```

Currently Curator only supports using Google Custom Search as an image search provider, and only a single set of API keys.  Google limits a single set of API keys to no more than 1200 results per minute, so this limits the ability of Curator to crawl large amounts of data in a single run. In the future "shopping-list.yaml" will accept multiple API keys for a single fun, and will also support other search providers (such as Bing). This will allow the application to acquire significantly more images during a single run of the search sub-command.

## Key Concepts

**Repository**
A repository is a collection of images together with all of the metadata about those images. Currently Curator only supports a `FileSystemImageRepository` implementation that stores all data locally in a specific directory. In the future there may be an implementation that stores data in a cloud-based BLOB storage, such as AWS S3 or GCP Storage Buckets. A repository is synonymous with its location. That is, a repository cannot be spread across more than one directory, nor can two different repositories exist with the same root directory.

All invocations of Curator must specify the repository location. However, if you are only using a single repository then you can store the path in the environment variable CURATOR_REPOSITORY_LOCATION so that you do not have to pass it explicitly each time. If you do pass the location explicitly, it mush be passed as an option to the curator command itself, not to the sub-commands. For example:
```bash
poetry run curator --repository-location ~/data/dogs-and-cats info
```

**Shopping List**
A `ShoppingList` is a YAML file that contains information about searches that the application should perform, as well as the search provider(s) used to perform the searches. This file is required to run the `curator search` command. By default Curator looks for a file named `shopping-list.yaml` located in the root directory of the repository, however you may explicitly specify any file that matches the expected YAML schema.

To create a sample file with the expected schema, you can use the `curator init` command, either specifying just "shopping-list" if all you want is the sample YAML file. A "shopping-list.yaml" file is also created if you use the `curator init all` command.
```bash
poetry run curator --repository-location ~/data/dogs-and-cats init shopping-list
```
