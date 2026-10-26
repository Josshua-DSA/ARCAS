"""Uji invarian konfigurasi profil alokasi (SCHEMA.md #10 & #11).

Latar: `SCHEMA.md` invarian #10 menuntut "Σ base_pct == 100.0 untuk setiap
profil; validasi saat memuat `alloc_profiles.yaml`". Sebelum uji ini, tidak ada
validasi apa pun: profil dengan Σ base_pct = 90 tetap dimuat tanpa error, lalu
`tilt_portfolio` menormalisasi ulang bobotnya sehingga hasilnya tampak benar
(Σ new_pct = 100) padahal proporsi yang dipakai bukan yang tertulis di YAML.
Kegagalan sunyi seperti itu lebih berbahaya daripada crash.
"""

from __future__ import annotations

import copy

import pytest
import yaml

from backend.src.alloc.engine import AllocationEngine, ProfileConfigError


def _valid_profiles() -> dict:
    """Profil minimal yang memenuhi invarian #10 & #11."""
    return {
        "profiles": {
            "demo": {
                "name": "Demo",
                "classes": {
                    "cash": {"base_pct": 40.0, "min_pct": 20.0, "max_pct": 60.0},
                    "equity": {"base_pct": 60.0, "min_pct": 30.0, "max_pct": 80.0},
                },
            }
        },
        "params": {"lambda_tilt": 0.15, "delta_max_pp": 5.0, "conf_min": 0.4},
    }


def _write(tmp_path, data: dict):
    path = tmp_path / "profiles.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _engine(tmp_path, data: dict) -> AllocationEngine:
    return AllocationEngine(
        profiles_path=_write(tmp_path, data),
        map_path=tmp_path / "does_not_exist.yaml",
    )


# ---------------------------------------------------------------------------
# YAML asli di repo harus tetap lolos
# ---------------------------------------------------------------------------


def test_repo_profiles_satisfy_invariant():
    """`data/alloc_profiles.yaml` yang sebenarnya harus valid."""
    engine = AllocationEngine()  # memakai path default repo
    assert engine.profiles, "profil tidak termuat"

    for profile_id, profile in engine.profiles.items():
        total = sum(float(c["base_pct"]) for c in profile["classes"].values())
        assert abs(total - 100.0) < 1e-6, f"{profile_id}: Σ base_pct = {total}"


# ---------------------------------------------------------------------------
# Penolakan konfigurasi yang melanggar
# ---------------------------------------------------------------------------


def test_valid_config_loads(tmp_path):
    engine = _engine(tmp_path, _valid_profiles())
    assert "demo" in engine.profiles


def test_sum_not_100_is_rejected(tmp_path):
    """Invarian #10: Σ base_pct != 100 harus gagal keras saat memuat.

    Inilah bug yang diperbaiki: sebelumnya profil ini dimuat tanpa keluhan,
    lalu dinormalisasi ulang secara diam-diam saat tilt.
    """
    data = _valid_profiles()
    data["profiles"]["demo"]["classes"]["cash"]["base_pct"] = 30.0  # Σ = 90

    with pytest.raises(ProfileConfigError) as excinfo:
        _engine(tmp_path, data)

    msg = str(excinfo.value)
    assert "demo" in msg
    assert "100.0" in msg


def test_sum_over_100_is_rejected(tmp_path):
    data = _valid_profiles()
    data["profiles"]["demo"]["classes"]["cash"]["base_pct"] = 50.0  # Σ = 110

    with pytest.raises(ProfileConfigError):
        _engine(tmp_path, data)


def test_base_outside_min_max_is_rejected(tmp_path):
    """Invarian #11: baseline harus berada di dalam [min_pct, max_pct]."""
    data = _valid_profiles()
    data["profiles"]["demo"]["classes"]["cash"] = {
        "base_pct": 70.0,
        "min_pct": 10.0,
        "max_pct": 20.0,
    }
    data["profiles"]["demo"]["classes"]["equity"]["base_pct"] = 30.0  # Σ tetap 100

    with pytest.raises(ProfileConfigError) as excinfo:
        _engine(tmp_path, data)
    assert "di luar rentang" in str(excinfo.value)


def test_missing_field_is_rejected(tmp_path):
    data = _valid_profiles()
    del data["profiles"]["demo"]["classes"]["cash"]["min_pct"]

    with pytest.raises(ProfileConfigError) as excinfo:
        _engine(tmp_path, data)
    assert "min_pct" in str(excinfo.value)


def test_empty_class_set_is_rejected(tmp_path):
    data = _valid_profiles()
    data["profiles"]["demo"]["classes"] = {}

    with pytest.raises(ProfileConfigError):
        _engine(tmp_path, data)


def test_error_names_the_offending_profile(tmp_path):
    """Pesan harus menyebut profil mana — YAML bisa berisi banyak profil."""
    data = _valid_profiles()
    broken = copy.deepcopy(data["profiles"]["demo"])
    broken["classes"]["cash"]["base_pct"] = 10.0
    data["profiles"]["rusak"] = broken

    with pytest.raises(ProfileConfigError) as excinfo:
        _engine(tmp_path, data)
    assert "rusak" in str(excinfo.value)


def test_floating_point_noise_is_tolerated(tmp_path):
    """Profil hasil pembulatan desimal tidak boleh ditolak."""
    data = _valid_profiles()
    data["profiles"]["demo"]["classes"]["cash"]["base_pct"] = 33.33
    data["profiles"]["demo"]["classes"]["equity"]["base_pct"] = 66.67

    engine = _engine(tmp_path, data)
    assert "demo" in engine.profiles
