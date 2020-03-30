from typing import Tuple

import torch
from torch import nn, Tensor
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class Encoder(nn.Module):
    """Encodes a sequence of word embeddings"""

    def __init__(self, input_size: int, hidden_size: int, num_layers: int, dropout: float) -> None:
        super(Encoder, self).__init__()
        self.num_layers = num_layers
        self.rnn = nn.LSTM(input_size, hidden_size, num_layers,
                           batch_first=True, bidirectional=True, dropout=dropout)

    def forward(self, x: Tensor, mask: Tensor, lengths: Tensor, sort=False) -> Tuple[Tensor, Tuple[Tensor, Tensor]]:
        """
        Applies a bidirectional LSTM to sequence of embeddings x.
        The input mini-batch x needs to be sorted by length.
        x should have dimensions [batch, time, dim].
        :param x: [B, SrcSeqLen, EmbCode]
        :param mask: [B, 1, SrcSeqLen]
        :param lengths: [B]
        :returns: Tuple[
            [B, SrcSeqLen, NumDirections * SrcEncoderH],
            Tuple[[NumLayers, B, NumDirections * SrcEncoderH], [NumLayers, B, NumDirections * SrcEncoderH]]
        ]
        """
        if sort:
            lengths, lengths_mask = torch.sort(lengths, descending=True)
            x = x[lengths_mask, :, :]
            packed = pack_padded_sequence(x, lengths,
                                          batch_first=True)  # [RealTokenNumberWithoutPad, AlignedSeqLen * 3]
            # packed seq, [NumLayers * NumDirections, B, DiffEncoderH], [NumLayers * NumDirections, B, DiffEncoderH]
            output, (h_n, c_n) = self.rnn(packed)
            output, _ = pad_packed_sequence(output,
                                            batch_first=True)  # [B, AlignedSeqLen, NumDirections * DiffEncoderH]

            # we need to manually concatenate the final states for both directions
            fwd_final = h_n[0:h_n.size(0):2]  # [NumLayers, B, DiffEncoderH]
            bwd_final = h_n[1:h_n.size(0):2]  # [NumLayers, B, DiffEncoderH]
            h_n = torch.cat([fwd_final, bwd_final], dim=2)  # [NumLayers, B, NumDirections * DiffEncoderH]
            fwd_cell = c_n[0:c_n.size(0):2]  # [NumLayers, B, DiffEncoderH]
            bwd_cell = c_n[1:c_n.size(0):2]  # [NumLayers, B, DiffEncoderH]
            c_n = torch.cat([fwd_cell, bwd_cell], dim=2)  # [NumLayers, B, NumDirections * DiffEncoderH]

            lengths_mask_reverse = torch.argsort(lengths_mask)
            return output[lengths_mask_reverse, :], (h_n[:, lengths_mask_reverse, :], c_n[:, lengths_mask_reverse, :])
        else:
            packed = pack_padded_sequence(x, lengths, batch_first=True)  # [RealTokenNumberWithoutPad, SecSeqLen]
            # packed seq, [NumLayers * NumDirections, B, SrcEncoderH], [NumLayers * NumDirections, B, SrcEncoderH]
            output, (h_n, c_n) = self.rnn(packed)
            output, _ = pad_packed_sequence(output, batch_first=True)  # [B, SrcSeqLen, NumDirections * SrcEncoderH]

            # we need to manually concatenate the final states for both directions
            fwd_final = h_n[0:h_n.size(0):2]  # [NumLayers, B, SrcEncoderH]
            bwd_final = h_n[1:h_n.size(0):2]  # [NumLayers, B, SrcEncoderH]
            h_n = torch.cat([fwd_final, bwd_final], dim=2)  # [NumLayers, B, NumDirections * SrcEncoderH]
            fwd_cell = c_n[0:c_n.size(0):2]  # [NumLayers, B, SrcEncoderH]
            bwd_cell = c_n[1:c_n.size(0):2]  # [NumLayers, B, SrcEncoderH]
            c_n = torch.cat([fwd_cell, bwd_cell], dim=2)  # [NumLayers, B, NumDirections * SrcEncoderH]

            return output, (h_n, c_n)
