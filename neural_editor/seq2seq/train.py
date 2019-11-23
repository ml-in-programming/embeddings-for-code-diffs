import os
import pprint
from typing import Tuple, List
import pickle
from pathlib import Path

import torch
from torch import nn
from torchtext import data
from torchtext.data import Field, Dataset

from neural_editor.seq2seq import EncoderDecoder
from neural_editor.seq2seq.SimpleLossCompute import SimpleLossCompute
from neural_editor.seq2seq.datasets.CodeChangesDataset import CodeChangesTokensDataset
from neural_editor.seq2seq.datasets.dataset_utils import load_datasets
from neural_editor.seq2seq.train_config import CONFIG
from neural_editor.seq2seq.train_utils import print_data_info, make_model, \
    run_epoch, rebatch, print_examples, plot_perplexity


def load_data(verbose: bool) -> Tuple[Dataset, Dataset, Dataset, Field]:
    diffs_field: Field = data.Field(batch_first=True, lower=CONFIG['LOWER'], include_lengths=True,
                                    unk_token=CONFIG['UNK_TOKEN'], pad_token=CONFIG['PAD_TOKEN'],
                                    init_token=CONFIG['SOS_TOKEN'],
                                    eos_token=CONFIG['EOS_TOKEN'])  # TODO: init_token=None?
    train_data, val_data, test_data = load_datasets(CodeChangesTokensDataset,
                                                    CONFIG['DATASET_ROOT'], diffs_field,
                                                    filter_pred=lambda x: len(vars(x)['src']) <= CONFIG[
                                                        'TOKENS_CODE_CHUNK_MAX_LEN'] and
                                                                          len(vars(x)['trg']) <= CONFIG[
                                                                              'TOKENS_CODE_CHUNK_MAX_LEN'])
    # TODO: consider building 2 vocabularies: one for (src, trg), second for diffs
    diffs_field.build_vocab(train_data.src, train_data.trg,
                            train_data.diff_alignment, train_data.diff_prev,
                            train_data.diff_updated, min_freq=CONFIG['TOKEN_MIN_FREQ'])
    if verbose:
        print_data_info(train_data, val_data, test_data, diffs_field)
    return train_data, val_data, test_data, diffs_field


def train(model: EncoderDecoder,
          train_data: Dataset, val_data: Dataset, diffs_field: Field,
          print_every: int) -> Tuple[List[float], List[float]]:
    """
    :param model: model to train
    :param train_data: train data
    :param val_data: validation data
    :param diffs_field: Field object from torchtext, stores vocabulary
    :param print_every: print every ith batch
    :return: train and validation perplexities for each epoch
    """
    # TODO: add early stopping and choosing best model on eval
    # TODO: why it is 0, maybe padding doesn't work because no tokenizing
    # optionally add label smoothing; see the Annotated Transformer
    pad_index: int = diffs_field.vocab.stoi[CONFIG['PAD_TOKEN']]
    criterion = nn.NLLLoss(reduction="sum", ignore_index=pad_index)
    optimizer = torch.optim.Adam(model.parameters(), lr=CONFIG['LEARNING_RATE'])

    train_iter = data.BucketIterator(train_data, batch_size=CONFIG['BATCH_SIZE'], train=True,
                                     shuffle=True,
                                     sort_within_batch=True,
                                     sort_key=lambda x: (len(x.src), len(x.trg)), repeat=False,
                                     device=CONFIG['DEVICE'])
    train_batches_num: int = len(train_iter)
    train_loss_function = SimpleLossCompute(model.generator, criterion, optimizer)
    train_perplexities = []

    val_iter = data.Iterator(val_data, batch_size=1, train=False, sort=False, repeat=False, device=CONFIG['DEVICE'])
    val_batches_num = len(val_iter)
    # noinspection PyTypeChecker
    # reason: None is not a type of Optimizer
    val_loss_function = SimpleLossCompute(model.generator, criterion, None)
    val_perplexities = []

    epochs_num: int = CONFIG['MAX_NUM_OF_EPOCHS']
    for epoch in range(epochs_num):
        print(f'Epoch {epoch} / {epochs_num}')
        model.train()
        train_perplexity = run_epoch((rebatch(pad_index, b) for b in train_iter),
                                     model, train_loss_function,
                                     train_batches_num,
                                     print_every=print_every)
        print(f'Train perplexity: {train_perplexity}')
        train_perplexities.append(train_perplexity)

        model.eval()
        with torch.no_grad():
            print_examples((rebatch(pad_index, x) for x in val_iter),
                           model, CONFIG['TOKENS_CODE_CHUNK_MAX_LEN'] + 10,
                           diffs_field.vocab, n=3)

            val_perplexity = run_epoch((rebatch(pad_index, t) for t in val_iter),
                                       model, val_loss_function,
                                       val_batches_num, print_every=print_every)
            print(f'Validation perplexity: {val_perplexity}')
            val_perplexities.append(val_perplexity)

        if epoch % CONFIG['SAVE_MODEL_EVERY'] == 0:
            torch.save(model, os.path.join(CONFIG['OUTPUT_PATH'], 'model.pt'))

    return train_perplexities, val_perplexities


def test(model: EncoderDecoder, test_data: Dataset, diffs_field: Field, print_every: int) -> float:
    """
    :param model: model to test
    :param test_data: test data
    :param diffs_field: Field object from torchtext
    :param print_every: not used
    :return: perplexity on test data
    """
    pad_index: int = diffs_field.vocab.stoi[CONFIG['PAD_TOKEN']]
    criterion = nn.NLLLoss(reduction="sum", ignore_index=pad_index)
    test_iter = data.Iterator(test_data, batch_size=1, train=False, sort=False, repeat=False, device=CONFIG['DEVICE'])
    test_batches_num = len(test_iter)
    # noinspection PyTypeChecker
    # reason: None is not a type of Optimizer
    test_loss_function = SimpleLossCompute(model.generator, criterion, None)
    model.eval()
    with torch.no_grad():
        print_examples((rebatch(pad_index, x) for x in test_iter),
                       model, CONFIG['TOKENS_CODE_CHUNK_MAX_LEN'] + 10,
                       diffs_field.vocab, n=3)

        test_perplexity = run_epoch((rebatch(pad_index, t) for t in test_iter),
                                    model, test_loss_function,
                                    test_batches_num, print_every=print_every)
        print(f'Test perplexity: {test_perplexity}')
        return test_perplexity


def run_experiment() -> None:
    pprint.pprint(CONFIG)
    with open(os.path.join(CONFIG['OUTPUT_PATH'], 'config.pkl'), 'wb') as config_file:
        pickle.dump(CONFIG, config_file)

    train_dataset, val_dataset, test_dataset, diffs_field = load_data(verbose=CONFIG['VERBOSE'])
    model: EncoderDecoder = make_model(len(diffs_field.vocab),
                                       edit_representation_size=CONFIG['EDIT_REPRESENTATION_SIZE'],
                                       emb_size=CONFIG['WORD_EMBEDDING_SIZE'],
                                       hidden_size_encoder=CONFIG['ENCODER_HIDDEN_SIZE'],
                                       hidden_size_decoder=CONFIG['DECODER_HIDDEN_SIZE'],
                                       num_layers=CONFIG['NUM_LAYERS'],
                                       dropout=CONFIG['DROPOUT'],
                                       use_bridge=CONFIG['USE_BRIDGE'])
    # noinspection PyTypeChecker
    # reason: PyCharm doesn't understand that EncoderDecoder is child of nn.Module
    train_perplexities, val_perplexities = train(model, train_dataset, val_dataset, diffs_field,
                                                 print_every=CONFIG['PRINT_EVERY_iTH_BATCH'])
    print(train_perplexities)
    print(val_perplexities)
    with open(os.path.join(CONFIG['OUTPUT_PATH'], 'train_perplexities.pkl'), 'wb') as train_file:
        pickle.dump(train_perplexities, train_file)
    with open(os.path.join(CONFIG['OUTPUT_PATH'], 'val_perplexities.pkl'), 'wb') as val_file:
        pickle.dump(val_perplexities, val_file)
    # noinspection PyTypeChecker
    # reason: PyCharm doesn't understand that EncoderDecoder is child of nn.Module
    test(model, test_dataset, diffs_field, print_every=-1)


if __name__ == "__main__":
    run_experiment()
