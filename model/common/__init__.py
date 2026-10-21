"""Shared ML components used by both the XAU and FOMC domain tracks.

Everything that is not specific to one corpus lives here: the inference
contract, the TF-IDF baseline algorithm, evaluation metrics, and the
cross-domain router weights. Domain-specific code belongs in `model/xau/`
or `model/fomc/`.
"""

__version__ = "0.6.0"
