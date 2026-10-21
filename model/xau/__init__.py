"""XAU (gold) sentiment track — FinBERT-EMAS.

Scope: model training, weights and evaluation for the gold corpus
(`dataset/gold_sinha/`), producing `p_pos, p_neu, p_neg` for the XAU target.

Shared contracts (inference protocol, metrics, baseline algorithm) come from
`model.common`; nothing in this package should duplicate them.
"""
