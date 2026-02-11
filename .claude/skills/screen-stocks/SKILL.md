---
name: screen-stocks
description: 割安株スクリーニング。PER/PBR/配当利回り/ROE等の指標で日本株・米国株・ASEAN株から割安銘柄を検索する。
argument-hint: "[market] [preset]  例: japan value, us high-dividend, asean quality"
allowed-tools: Bash(python3 *)
---

# 割安株スクリーニングスキル

$ARGUMENTS を解析して market と preset を判定し、以下のコマンドを実行してください。

## 実行コマンド

```bash
python3 /Users/kikuchihiroyuki/stock-skills/.claude/skills/screen-stocks/scripts/run_screen.py --market <market> --preset <preset>
```

## 引数の解釈ルール

- 第1引数: market (japan / us / asean / all) デフォルト: japan
- 第2引数: preset (value / high-dividend / growth-value / deep-value / quality / sharpe-ratio) デフォルト: value
- 「高配当」→ high-dividend、「米国株」→ us、「割安」→ value、「成長」→ growth-value、「シャープ」→ sharpe-ratio

## 対応市場

- `japan` : 日本株（日経225主要銘柄）
- `us` : 米国株（S&P500主要銘柄）
- `asean` : ASEAN株（シンガポール、タイ、マレーシア、インドネシア、フィリピン）
- `all` : 全市場

## プリセット

- `value` : 伝統的バリュー投資（低PER・低PBR）
- `high-dividend` : 高配当株（配当利回り3%以上）
- `growth-value` : 成長バリュー（成長性＋割安度）
- `deep-value` : ディープバリュー（非常に低いPER/PBR）
- `quality` : クオリティバリュー（高ROE＋割安）
- `sharpe-ratio` : シャープレシオ最適化（5条件フレームワーク。低ボラ・割安・財務安定・EPS成長で選別。実行に時間がかかります）

## 出力

結果はMarkdown表形式で表示してください。
