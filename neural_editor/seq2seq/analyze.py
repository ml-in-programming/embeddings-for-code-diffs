import os
import pprint
import sys
import time
from datetime import timedelta
from pathlib import Path

import torch

from datasets.CodeChangesDataset import CodeChangesTokensDataset
from neural_editor.seq2seq import EncoderDecoder
from neural_editor.seq2seq.config import Config, load_config
from datasets.dataset_utils import take_part_from_dataset, load_tufano_dataset
from neural_editor.seq2seq.experiments.AccuracyCalculation import AccuracyCalculation
from neural_editor.seq2seq.experiments.EditRepresentationVisualization import EditRepresentationVisualization
from neural_editor.seq2seq.experiments.OneShotLearning import OneShotLearning
from neural_editor.seq2seq.test_utils import load_defects4j_dataset, load_labeled_dataset


def measure_experiment_time(func) -> None:
    start = time.time()
    func()
    end = time.time()
    print(f'Duration: {str(timedelta(seconds=end - start))}')
    print()


def test_commit_message_generation_model(model: EncoderDecoder, config: Config) -> None:
    # TODO: implement testing of commit message generation model
    pass


def test_neural_editor_model(model: EncoderDecoder, config: Config) -> None:
    train_dataset, val_dataset, test_dataset, diffs_field = \
        CodeChangesTokensDataset.load_data(verbose=True, config=config)
    tufano_labeled_0_50_dataset, tufano_labeled_0_50_classes = \
        load_labeled_dataset(config['TUFANO_LABELED_0_50_PATH'], diffs_field, config)
    tufano_labeled_50_100_dataset, tufano_labeled_50_100_classes = \
        load_labeled_dataset(config['TUFANO_LABELED_50_100_PATH'], diffs_field, config)
    defects4j_dataset, defects4j_classes = load_defects4j_dataset(diffs_field, config)
    tufano_bug_fixes_0_50_dataset_train, tufano_bug_fixes_0_50_dataset_val, tufano_bug_fixes_0_50_dataset_test = \
        load_tufano_dataset(config['TUFANO_BUG_FIXES_0_50_PATH'], diffs_field, config)
    tufano_bug_fixes_50_100_dataset_train, tufano_bug_fixes_50_100_dataset_val, tufano_bug_fixes_50_100_dataset_test = \
        load_tufano_dataset(config['TUFANO_BUG_FIXES_50_100_PATH'], diffs_field, config)
    tufano_code_changes_0_50_dataset_train, tufano_code_changes_0_50_dataset_val, tufano_code_changes_0_50_dataset_test = \
        load_tufano_dataset(config['TUFANO_CODE_CHANGES_0_50_PATH'], diffs_field, config)
    tufano_code_changes_50_100_dataset_train, tufano_code_changes_50_100_dataset_val, tufano_code_changes_50_100_dataset_test = \
        load_tufano_dataset(config['TUFANO_CODE_CHANGES_50_100_PATH'], diffs_field, config)

    one_shot_learning_experiment = OneShotLearning(model, diffs_field, config)
    accuracy_calculation_experiment = AccuracyCalculation(model, diffs_field, config)
    visualization_experiment = EditRepresentationVisualization(model, diffs_field, config)

    model.eval()
    model.unset_edit_representation()
    with torch.no_grad():
        # Visualization of data
        measure_experiment_time(
            lambda: visualization_experiment.conduct(tufano_labeled_0_50_dataset,
                                                     'tufano_labeled_0_50_2d_representations.png',
                                                     classes=tufano_labeled_0_50_classes)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(tufano_labeled_0_50_dataset,
                                                     'tufano_labeled_0_50_2d_representations_8_threshold.png',
                                                     classes=tufano_labeled_0_50_classes,
                                                     threshold=8)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(tufano_labeled_50_100_dataset,
                                                     'tufano_labeled_50_100_2d_representations.png',
                                                     classes=tufano_labeled_50_100_classes)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(tufano_labeled_50_100_dataset,
                                                     'tufano_labeled_50_100_2d_representations_8_threshold.png',
                                                     classes=tufano_labeled_50_100_classes,
                                                     threshold=8)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(defects4j_dataset,
                                                     'defects4j_2d_representations.png',
                                                     classes=defects4j_classes)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(take_part_from_dataset(test_dataset, 300),
                                                     'test300_2d_representations.png', classes=None)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(take_part_from_dataset(val_dataset, 300),
                                                     'val300_2d_representations.png', classes=None)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(take_part_from_dataset(train_dataset, 300),
                                                     'train300_2d_representations.png', classes=None)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(test_dataset,
                                                     'test_2d_representations.png', classes=None)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(val_dataset,
                                                     'val_2d_representations.png', classes=None)
        )
        measure_experiment_time(
            lambda: visualization_experiment.conduct(take_part_from_dataset(train_dataset, 5000),
                                                     'train5000_2d_representations.png', classes=None)
        )

        # Accuracy
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(tufano_labeled_0_50_dataset,
                                                            'Tufano Labeled 0 50 Code Changes')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(tufano_labeled_50_100_dataset,
                                                            'Tufano Labeled 50 100 Code Changes')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(defects4j_dataset, 'Defects4J')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(test_dataset, 300), 'Test dataset 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(val_dataset, 300), 'Validation dataset 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(train_dataset, 300), 'Train dataset 300')
        )

        # One shot learning
        measure_experiment_time(
            lambda: one_shot_learning_experiment.conduct(tufano_labeled_0_50_dataset, tufano_labeled_0_50_classes,
                                                         'Tufano Labeled 0 50 Code Changes')
        )
        measure_experiment_time(
            lambda: one_shot_learning_experiment.conduct(tufano_labeled_50_100_dataset, tufano_labeled_50_100_classes,
                                                         'Tufano Labeled 50 100 Code Changes')
        )
        measure_experiment_time(
            lambda: one_shot_learning_experiment.conduct(defects4j_dataset, defects4j_classes, 'Defects4J')
        )

        print('Starting long experiments', flush=True)

        # Whole test accuracy
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                test_dataset, 'Test dataset all')
        )

        # Tufano accuracy evaluation
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_0_50_dataset_train, 300),
                'Tufano bug fixes 0 50 dataset train 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_0_50_dataset_val, 300),
                'Tufano bug fixes 0 50 dataset val 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_0_50_dataset_test, 300),
                'Tufano bug fixes 0 50 dataset test 300')
        )

        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_50_100_dataset_train, 300),
                'Tufano bug fixes 50 100 dataset train 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_50_100_dataset_val, 300),
                'Tufano bug fixes 50 100 dataset val 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_bug_fixes_50_100_dataset_test, 300),
                'Tufano bug fixes 50 100 dataset test 300')
        )

        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_0_50_dataset_train, 300),
                'Tufano code changes 0 50 dataset train 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_0_50_dataset_val, 300),
                'Tufano code changes 0 50 dataset val 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_0_50_dataset_test, 300),
                'Tufano code changes 0 50 dataset test 300')
        )

        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_50_100_dataset_train, 300),
                'Tufano code changes 50 100 dataset train 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_50_100_dataset_val, 300),
                'Tufano code changes 50 100 dataset val 300')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                take_part_from_dataset(tufano_code_changes_50_100_dataset_test, 300),
                'Tufano code changes 50 100 dataset test 300')
        )

        # All test data Tufano dataset evaluation
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                tufano_bug_fixes_0_50_dataset_test, 'Tufano bug fixes 0 50 dataset test')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                tufano_bug_fixes_50_100_dataset_test, 'Tufano bug fixes 50 100 dataset test')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                tufano_code_changes_0_50_dataset_test, 'Tufano code changes 0 50 dataset test')
        )
        measure_experiment_time(
            lambda: accuracy_calculation_experiment.conduct(
                tufano_code_changes_50_100_dataset_test, 'Tufano code changes 50 100 dataset test')
        )


def print_results(results_root: str, config: Config) -> None:
    pprint.pprint(config.get_config())
    print('\n====STARTING NEURAL EDITOR EVALUATION====\n', end='')
    neural_editor = torch.load(os.path.join(results_root, 'model_best_on_validation_neural_editor.pt'),
                               map_location=config['DEVICE'])
    test_neural_editor_model(neural_editor, config)
    print('\n====STARTING COMMIT MSG GENERATOR EVALUATIONN====\n', end='')
    commit_msg_generator = torch.load(os.path.join(results_root, 'model_best_on_validation_commit_msg_generator.pt'),
                                      map_location=config['DEVICE'])
    test_commit_message_generation_model(commit_msg_generator, config)


def main() -> None:
    if len(sys.argv) != 3 and len(sys.argv) != 2:
        print("arguments: <results_root_dir> <is_test (optional, default false)>.")
    results_root_dir = sys.argv[1]
    is_test = len(sys.argv) > 2 and sys.argv[2] == 'test'
    config_path = Path(results_root_dir).joinpath('config.pkl')
    config = load_config(is_test, config_path)
    print_results(results_root_dir, config)


if __name__ == "__main__":
    main()
