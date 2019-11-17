from neural_editor.seq2seq.train_config import CONFIG


class Batch:
    """Object for holding a batch of data with mask during training.
    Input is a batch from a torch text iterator.
    """

    def __init__(self, src, trg, diff_alignment, diff_prev, diff_updated, pad_index=0):
        src, src_lengths = src

        self.diff_alignment, self.diff_alignment_lengths = diff_alignment
        self.diff_alignment_mask = (self.diff_alignment != pad_index).unsqueeze(-2)
        self.diff_prev, self.diff_prev_lengths = diff_prev
        self.diff_prev_mask = (self.diff_prev != pad_index).unsqueeze(-2)
        self.diff_updated, self.diff_updated_lengths = diff_updated
        self.diff_updated_mask = (self.diff_updated != pad_index).unsqueeze(-2)

        self.src = src
        self.src_lengths = src_lengths
        self.src_mask = (src != pad_index).unsqueeze(-2)
        self.nseqs = src.size(0)

        self.trg = None
        self.trg_y = None
        self.trg_mask = None
        self.trg_lengths = None
        self.ntokens = None

        if trg is not None:
            trg, trg_lengths = trg
            self.trg = trg[:, :-1]  # TODO: what is that? it is padding, why it isn't eos token? Answer: it is problem because not all samples in batch have the same size therefore padding is cut
            self.trg_lengths = trg_lengths
            self.trg_y = trg[:, 1:]
            self.trg_mask = (self.trg_y != pad_index)
            self.ntokens = (self.trg_y != pad_index).data.sum().item()

        if CONFIG['USE_CUDA']:
            self.src = self.src.cuda()
            self.src_mask = self.src_mask.cuda()

            if trg is not None:
                self.trg = self.trg.cuda()
                self.trg_y = self.trg_y.cuda()
                self.trg_mask = self.trg_mask.cuda()
