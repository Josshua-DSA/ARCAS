"""FOMC sentiment track — FOMC-RoBERTa.

Scope: model training, weights and evaluation for the FOMC corpus
(`dataset/fomc/`), producing hawkish/dovish stances mapped to RATE_UST and SPX.

Shared contracts (inference protocol, metrics, baseline algorithm) come from
`model.common`; nothing in this package should duplicate them.
"""
