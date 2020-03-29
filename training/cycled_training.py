#! /usr/bin/env python

import argparse
import os
import shutil
import subprocess

import numpy as np
import pandas as pd

# ======================================================================================================================

steps_per_dataset = 5
start_with_english_checkpoint = 1

# ======================================================================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run cycled training')
    parser.add_argument('checkpoint_path', type=str)
    parser.add_argument('prepared_data_path', type=str)
    parser.add_argument('data_appendix', type=str)
    parser.add_argument('--tuda', action='store_true')
    parser.add_argument('--voxforge', action='store_true')
    parser.add_argument('--mailabs', action='store_true')
    parser.add_argument('--swc', action='store_true')
    parser.add_argument('--common_voice', action='store_true')
    args = parser.parse_args()

    datasets = []

    if args.tuda:
        datasets.append("tuda")
    if args.voxforge:
        datasets.append("voxforge")
    if args.mailabs:
        datasets.append("mailabs")
    if args.swc:
        datasets.append("swc")
    if args.common_voice:
        datasets.append("common_voice")

    if (len(datasets) == 0):
        print("No datasets to train with")
        exit()

    data_train_all = None
    data_dev_all = None
    data_test_all = None
    data_path_cycled = os.path.join(args.prepared_data_path, "cycled_data")
    data_train_path_cycled = os.path.join(data_path_cycled, "train.csv")
    data_dev_path_cycled = os.path.join(data_path_cycled, "dev.csv")
    data_test_path_cycled = os.path.join(data_path_cycled, "test.csv")

    if (os.path.isdir(data_path_cycled)):
        shutil.rmtree(data_path_cycled)
    os.mkdir(data_path_cycled)

    # Create dev and test dataset
    for d in datasets:
        data_dev_path = os.path.join(args.prepared_data_path, d, "dev" + args.data_appendix + ".csv")
        data_dev = pd.read_csv(data_dev_path, keep_default_na=False)
        data_test_path = os.path.join(args.prepared_data_path, d, "test" + args.data_appendix + ".csv")
        data_test = pd.read_csv(data_test_path, keep_default_na=False)

        if (data_dev_all is None):
            data_dev_all = data_dev
        else:
            data_dev_all = pd.concat([data_dev_all, data_dev])
        if (data_test_all is None):
            data_test_all = data_test
        else:
            data_test_all = pd.concat([data_test_all, data_test])

    # Shuffle them
    data_dev_all = data_dev_all.iloc[np.random.permutation(len(data_dev_all))]
    data_test_all = data_test_all.iloc[np.random.permutation(len(data_test_all))]
    # And save them to a file
    data_dev_all.to_csv(data_dev_path_cycled, index=False, encoding='utf-8')
    data_test_all.to_csv(data_test_path_cycled, index=False, encoding='utf-8')

    # Run the cycled training
    for d in datasets:
        data_train_path = os.path.join(args.prepared_data_path, d, "train" + args.data_appendix + ".csv")
        data_train = pd.read_csv(data_train_path, keep_default_na=False)
        print("\nStarted to add a new dataset with {} entries".format(len(data_train)))

        for i in range(steps_per_dataset):
            split_size = int(len(data_train) / steps_per_dataset)
            split_start = split_size * i
            # Don't miss out data at the end if split was not even
            split_end = split_size * (i + 1) if (i != steps_per_dataset - 1) else len(data_train)

            data_train_split = data_train[split_size * i:split_size * (i + 1)]

            if (data_train_all is None):
                data_train_all = data_train_split
            else:
                data_train_all = pd.concat([data_train_all, data_train_split])

            # Shuffle and save as file
            data_train_all = data_train_all.iloc[np.random.permutation(len(data_train_all))]
            data_train_all.to_csv(data_train_path_cycled, index=False, encoding='utf-8')

            cmd = "/bin/bash deepspeech-german/training/train.sh " + args.checkpoint_path + " " + \
                  data_train_path_cycled + " " + data_dev_path_cycled + " " + data_test_path_cycled + \
                  " 0 " + str(start_with_english_checkpoint)

            if (start_with_english_checkpoint == 1):
                start_with_english_checkpoint = 0

            print("\nRunning next trainstep with {} training instances".format(len(data_train_all)))
            sp = subprocess.Popen(['/bin/bash', '-c', cmd])
            sp.wait()
