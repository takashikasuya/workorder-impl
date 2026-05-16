#!/usr/bin/env python3
"""
workorder-impl と workorder-systems/systems.yaml の整合性を検証する。

チェック内容:
  1. CS 存在確認  : systems.yaml の CS-* ごとに services/<dir>/ が存在する
  2. FUN カバレッジ: systems.yaml の FUN-* が、対応 CS のサービスディレクトリ内
                    いずれかの .py ファイルに登場する
  3. IF カバレッジ : systems.yaml の IF-* がリポジトリ内いずれかの
                    .py ファイルに登場する
  4. 逆引き確認  : .py ファイル内の FUN-*/IF-* が systems.yaml に定義されているか警告

使い方:
  python scripts/validate_arch_sync.py \\
      --systems-dir ../workorder-systems \\
      --impl-dir .
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

CS_RE = re.compile(r"\bCS-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
FUN_RE = re.compile(r"\bFUN-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+\b")
IF_RE = re.compile(r"\bIF-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+\b")


def cs_to_dir(cs_id: str) -> str:
    """CS-OBS-COLLECTOR -> obs_collector"""
    return cs_id.removeprefix("CS-").lower().replace("-", "_")


def ids_in_text(text: str) -> tuple[set[str], set[str], set[str]]:
    return set(CS_RE.findall(text)), set(FUN_RE.findall(text)), set(IF_RE.findall(text))


def grep_dir(directory: Path, pattern: str) -> bool:
    """ディレクトリ以下のいずれかの .py ファイルに pattern が含まれるか。"""
    for py in directory.rglob("*.py"):
        if pattern in py.read_text(errors="replace"):
            return True
    return False


def grep_repo(impl_dir: Path, pattern: str) -> bool:
    for py in impl_dir.rglob("*.py"):
        if ".venv" in py.parts:
            continue
        if pattern in py.read_text(errors="replace"):
            return True
    return False


# ── YAML 構造パーサ ──────────────────────────────────────────────────


def _collect_ids(subtree) -> tuple[set[str], set[str], set[str]]:
    """YAML サブツリーを stringify して FUN/IF/CS を抽出する。"""
    text = yaml.dump(subtree, allow_unicode=True)
    return ids_in_text(text)


def parse_cs_map(data) -> dict[str, dict[str, set[str]]]:
    """
    systems.yaml から {cs_id: {"funs": {...}, "ifs": {...}}} を構築する。

    以下の YAML 構造を想定（どちらでも動作）:

    # 構造 A: CS-ID をキーとする dict
    components:
      CS-OBS-COLLECTOR:
        functions: [FUN-OBS-001, ...]
        interfaces: [IF-OBS-001, ...]

    # 構造 B: id キーを持つリスト
    components:
      - id: CS-OBS-COLLECTOR
        functions: [FUN-OBS-001, ...]
        interfaces: [IF-OBS-001, ...]
    """
    result: dict[str, dict[str, set[str]]] = {}

    def ensure(cs_id: str) -> dict[str, set[str]]:
        if cs_id not in result:
            result[cs_id] = {"funs": set(), "ifs": set()}
        return result[cs_id]

    def walk(node) -> None:
        if isinstance(node, dict):
            # 構造 A: キー自体が CS-*
            cs_keys = [k for k in node if isinstance(k, str) and CS_RE.fullmatch(k)]
            if cs_keys:
                for cs_id in cs_keys:
                    _, funs, ifs = _collect_ids(node[cs_id])
                    entry = ensure(cs_id)
                    entry["funs"].update(funs)
                    entry["ifs"].update(ifs)
                return

            # 構造 B: 値に CS-* が入っている（id / cs-id / cs_id キーなど）
            cs_id = None
            for id_key in ("id", "cs-id", "cs_id", "name", "component"):
                val = node.get(id_key)
                if val and isinstance(val, str) and CS_RE.fullmatch(val.strip()):
                    cs_id = val.strip()
                    break

            if cs_id:
                _, funs, ifs = _collect_ids(node)
                entry = ensure(cs_id)
                entry["funs"].update(funs)
                entry["ifs"].update(ifs)
            else:
                for v in node.values():
                    walk(v)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)

    # フォールバック: 構造パースで CS が1件も取れなかったらテキスト全抽出
    if not result:
        text = yaml.dump(data, allow_unicode=True)
        cs_ids, fun_ids, if_ids = ids_in_text(text)
        for cs_id in cs_ids:
            ensure(cs_id)
        # FUN/IF は CS に紐付けられないので all-repo チェックに委ねる
        result["__global__"] = {"funs": fun_ids, "ifs": if_ids}

    return result


# ── メイン検証 ────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--systems-dir", required=True, type=Path,
        help="workorder-systems リポジトリのルートパス",
    )
    parser.add_argument(
        "--impl-dir", default=Path("."), type=Path,
        help="workorder-impl リポジトリのルートパス（デフォルト: .）",
    )
    parser.add_argument(
        "--systems-file", default="systems.yaml",
        help="systems.yaml のファイル名（デフォルト: systems.yaml）",
    )
    args = parser.parse_args()

    systems_yaml = args.systems_dir / args.systems_file
    if not systems_yaml.exists():
        # ルートに見つからなければリポジトリ内を再帰検索
        candidates = sorted(args.systems_dir.rglob(args.systems_file))
        if candidates:
            systems_yaml = candidates[0]
            print(f"INFO: {args.systems_file} を {systems_yaml} で発見しました")
        else:
            yaml_files = sorted(args.systems_dir.rglob("*.yaml")) + sorted(args.systems_dir.rglob("*.yml"))
            print(f"ERROR: {args.systems_file} が {args.systems_dir} 以下に見つかりません", file=sys.stderr)
            print("  検出された YAML ファイル:", file=sys.stderr)
            for f in yaml_files[:20]:
                print(f"    {f.relative_to(args.systems_dir)}", file=sys.stderr)
            sys.exit(1)

    data = yaml.safe_load(systems_yaml.read_text())
    cs_map = parse_cs_map(data)

    services_root = args.impl_dir / "services"
    errors: list[str] = []
    warnings: list[str] = []

    # ── グローバル ID 集計 ────────────────────────────────────────────
    all_sys_funs: set[str] = set()
    all_sys_ifs: set[str] = set()
    for entry in cs_map.values():
        all_sys_funs.update(entry["funs"])
        all_sys_ifs.update(entry["ifs"])

    print("=" * 60)
    print("1. CS ディレクトリ存在チェック")
    print("=" * 60)
    for cs_id in sorted(k for k in cs_map if k != "__global__"):
        service_dir = services_root / cs_to_dir(cs_id)
        if service_dir.exists():
            print(f"  OK  {cs_id:40s} → {service_dir.name}/")
        else:
            errors.append(
                f"CS missing: {cs_id} → services/{cs_to_dir(cs_id)}/ が存在しない"
            )
            print(f"  NG  {cs_id:40s} → services/{cs_to_dir(cs_id)}/ ★missing")

    print()
    print("=" * 60)
    print("2. FUN-* カバレッジチェック（対応 CS サービスディレクトリ内）")
    print("=" * 60)
    for cs_id in sorted(k for k in cs_map if k != "__global__"):
        service_dir = services_root / cs_to_dir(cs_id)
        for fun_id in sorted(cs_map[cs_id]["funs"]):
            all_sys_funs.add(fun_id)
            if not service_dir.exists():
                continue  # CS チェックで既に報告済み
            if grep_dir(service_dir, fun_id):
                print(f"  OK  {fun_id:30s} in {service_dir.name}/")
            else:
                errors.append(
                    f"FUN uncovered: {fun_id} が"
                    f" services/{cs_to_dir(cs_id)}/ に見つからない"
                )
                print(f"  NG  {fun_id:30s} in {service_dir.name}/ ★missing")

    # __global__ フォールバック分はリポジトリ全体で検索
    for fun_id in sorted(cs_map.get("__global__", {}).get("funs", [])):
        if grep_repo(args.impl_dir, fun_id):
            print(f"  OK  {fun_id:30s} (repo-wide)")
        else:
            errors.append(f"FUN uncovered: {fun_id} がリポジトリ内に見つからない")
            print(f"  NG  {fun_id:30s} (repo-wide) ★missing")

    print()
    print("=" * 60)
    print("3. IF-* カバレッジチェック（リポジトリ全体）")
    print("=" * 60)
    for if_id in sorted(all_sys_ifs | cs_map.get("__global__", {}).get("ifs", set())):
        if grep_repo(args.impl_dir, if_id):
            print(f"  OK  {if_id}")
        else:
            errors.append(f"IF uncovered: {if_id} がリポジトリ内に見つからない")
            print(f"  NG  {if_id} ★missing")

    print()
    print("=" * 60)
    print("4. 逆引き確認（impl 内の FUN-*/IF-* が systems.yaml に定義されているか）")
    print("=" * 60)
    impl_funs: set[str] = set()
    impl_ifs: set[str] = set()
    for py in args.impl_dir.rglob("*.py"):
        if ".venv" in py.parts:
            continue
        text = py.read_text(errors="replace")
        impl_funs.update(FUN_RE.findall(text))
        impl_ifs.update(IF_RE.findall(text))

    stale_funs = impl_funs - all_sys_funs
    stale_ifs = impl_ifs - all_sys_ifs
    for f in sorted(stale_funs):
        warnings.append(f"WARN FUN stale: {f} は systems.yaml に未定義")
        print(f"  WARN {f} は systems.yaml に未定義")
    for i in sorted(stale_ifs):
        warnings.append(f"WARN IF stale: {i} は systems.yaml に未定義")
        print(f"  WARN {i} は systems.yaml に未定義")
    if not stale_funs and not stale_ifs:
        print("  OK  stale 参照なし")

    # ── サマリー ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    cs_count = len([k for k in cs_map if k != "__global__"])
    print(
        f"結果: CS={cs_count}  FUN={len(all_sys_funs)}  IF={len(all_sys_ifs)}"
        f"  errors={len(errors)}  warnings={len(warnings)}"
    )
    if errors:
        print("\nERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print("すべてのチェックが通過しました。")


if __name__ == "__main__":
    main()
