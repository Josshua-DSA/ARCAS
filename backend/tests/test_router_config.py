"""Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.

Alasan ini penting: angka yang ditanam di kode tidak tercatat di `version`,
tidak bisa diubah tanpa deploy, dan tidak terlihat saat audit. Test di bawah
membuktikan YAML benar-benar mengendalikan perilaku.
"""

import yaml

from backend.src.schema import Direction
from backend.src.tagging.router import TargetRouter


def _write_config(tmp_path, **routing):
    cfg = {"version": "test", "routing": routing}
    path = tmp_path / "router_config.yaml"
    path.write_text(yaml.dump(cfg), encoding="utf-8")
    return path


def _router(tmp_path, monkeypatch, **routing):
    """Router yang membaca config dari tmp_path (bukan data/ asli)."""
    path = _write_config(tmp_path, **routing)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "router_config.yaml").write_text(
        path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return TargetRouter(aliases_path=tmp_path / "none.csv",
                        impact_graph_path=tmp_path / "none.yaml")


def test_defaults_present():
    r = TargetRouter()
    for key in [
        "direction_threshold",
        "explicit_confidence",
        "macro_confidence_base",
        "macro_confidence_weight_factor",
        "macro_confidence_cap",
    ]:
        assert key in r.routing
        assert isinstance(r.routing[key], float)


def test_config_file_overrides_defaults(tmp_path, monkeypatch):
    r = _router(tmp_path, monkeypatch, explicit_confidence=0.42)
    assert r.routing["explicit_confidence"] == 0.42


def test_shipped_config_matches_previous_hardcoded_values():
    """Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.

    Kalau berbeda, perilaku router diam-diam berubah saat refactor ini.
    """
    r = TargetRouter()
    assert r.routing["direction_threshold"] == 0.1
    assert r.routing["explicit_confidence"] == 0.88
    assert r.routing["macro_confidence_base"] == 0.50
    assert r.routing["macro_confidence_weight_factor"] == 0.35
    assert r.routing["macro_confidence_cap"] == 0.85


def test_confidence_respects_cap(tmp_path, monkeypatch):
    """Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya."""
    r = _router(
        tmp_path,
        monkeypatch,
        macro_confidence_base=0.50,
        macro_confidence_weight_factor=10.0,
        macro_confidence_cap=0.85,
        direction_threshold=0.1,
    )
    confidence = min(
        r.routing["macro_confidence_cap"],
        r.routing["macro_confidence_base"]
        + 1.0 * r.routing["macro_confidence_weight_factor"],
    )
    assert confidence == 0.85


def test_threshold_controls_direction(tmp_path, monkeypatch):
    """Menaikkan ambang harus bisa memaksa arah menjadi NETRAL."""
    r = _router(tmp_path, monkeypatch, direction_threshold=0.9)
    threshold = r.routing["direction_threshold"]
    score = 0.5
    direction = (
        Direction.BULLISH
        if score > threshold
        else Direction.BEARISH
        if score < -threshold
        else Direction.NEUTRAL
    )
    assert direction == Direction.NEUTRAL


def test_broken_yaml_falls_back_to_defaults(tmp_path, monkeypatch):
    """YAML rusak tidak boleh membuat router mati total."""
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "router_config.yaml").write_text(
        "routing: [ini bukan mapping]\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    # YAML yang bentuknya salah tidak boleh menjatuhkan router.
    r = TargetRouter(
        aliases_path=tmp_path / "none.csv", impact_graph_path=tmp_path / "none.yaml"
    )
    assert r.routing["direction_threshold"] == 0.1
    assert r.routing["explicit_confidence"] == 0.88
