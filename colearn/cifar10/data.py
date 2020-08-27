import imgaug.augmenters as iaa
import tensorflow.keras.datasets.cifar10 as cifar10
import numpy as np

from colearn.data import shuffle_data
from colearn.data import split_by_chunksizes
from colearn.model import LearnerData
from pathlib import Path
import os, pickle, shutil


def split_to_folders(config, data_dir="", output_folder=Path(os.getcwd()) / "cifar"):
    # Load CIFAR
    (train_images, train_labels), (test_images, test_labels) = cifar10.load_data()
    all_images = np.concatenate([train_images, test_images], axis=0)
    all_labels = np.concatenate([train_labels, test_labels], axis=0)

    # Normalization
    all_images = all_images.astype("float32") / 255.0

    [all_images, all_labels] = shuffle_data(
        [all_images, all_labels], config.shuffle_seed
    )

    [all_images_lists, all_labels_lists] = split_by_chunksizes(
        [all_images, all_labels], config.data_split
    )

    dir_names = []
    for i in range(config.n_learners):

        dir_name = output_folder / str(i)
        dir_names.append(dir_name)
        if os.path.isdir(str(dir_name)):
            shutil.rmtree(str(dir_name))
            os.makedirs(str(dir_name))
        else:
            os.makedirs(str(dir_name))

        pickle.dump(all_images_lists[i], open(dir_name / "images.pickle", "wb"))
        pickle.dump(all_labels_lists[i], open(dir_name / "labels.pickle", "wb"))

    return dir_names


def prepare_single_client(config, data_dir):
    data = LearnerData()
    data.train_batch_size = config.batch_size

    images = pickle.load(open(Path(data_dir) / "images.pickle", "rb"))
    labels = pickle.load(open(Path(data_dir) / "labels.pickle", "rb"))

    [[train_images, test_images], [train_labels, test_labels]] = split_by_chunksizes(
        [images, labels], [config.train_ratio, config.test_ratio]
    )

    data.train_data_size = len(train_images)

    data.train_gen = train_generator(
        train_images, train_labels, config.batch_size, config, config.train_augment
    )
    data.val_gen = train_generator(
        train_images, train_labels, config.batch_size, config, config.train_augment
    )

    data.test_data_size = len(test_images)

    data.test_gen = train_generator(
        test_images,
        test_labels,
        config.batch_size,
        config,
        config.train_augment,
        shuffle=False,
    )

    data.test_batch_size = config.batch_size
    return data


# Augmentation sequence
seq_cifar = iaa.Sequential([iaa.Affine(rotate=(-15, 15))])  # rotation


def train_generator(data, labels, batch_size, config, augmentation=True, shuffle=True):
    # Get total number of samples in the data
    n_data = len(data)

    # Define two numpy arrays for containing batch data and labels
    batch_data = np.zeros(
        (batch_size, config.width, config.height, 3), dtype=np.float32
    )
    batch_labels = np.zeros((batch_size, 1), dtype=np.uint8)

    # Get a numpy array of all the indices of the input data
    indices = np.arange(n_data)

    if shuffle:
        if config.generator_seed is not None:
            np.random.seed(config.generator_seed)

        np.random.shuffle(indices)
    it = 0

    # Initialize a counter
    batch_counter = 0

    while True:
        if augmentation:
            batch_data[batch_counter] = seq_cifar.augment_image(data[indices[it]])
        else:
            batch_data[batch_counter] = data[indices[it]]

        batch_labels[batch_counter] = labels[indices[it]]

        batch_counter += 1
        it += 1

        if it >= n_data:
            it = 0

            if shuffle:
                if config.generator_seed is not None:
                    np.random.seed(config.generator_seed)
                np.random.shuffle(indices)

        if batch_counter == batch_size:
            yield batch_data, batch_labels
            batch_counter = 0