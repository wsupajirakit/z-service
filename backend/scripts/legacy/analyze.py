#!/usr/bin/env python3
import os
import sys
import glob
import json
import argparse
import pandas as pd
import numpy as np

def parse_args():
    parser = argparse.ArgumentParser(description="Analyze zTrade exported CSVs and extract traps, watch, and kill candidates.")
    parser.add_argument(
        "--dir", 
        type=str, 
        default=os.path.expanduser("~/Downloads"), 
        help="Directory containing the ztrade CSV exports (default: ~/Downloads)"
    )
    return parser.parse_args()

def find_latest_exports(dir_path):
    files = {
        'formula': None,
        '1h_part1': None,
        '1h_part2': None,
        '4h_part1': None,
        '4h_part2': None,
        '1d_part1': None,
        '1d_part2': None,
        '1w_part1': None,
        '1w_part2': None,
    }
    
    patterns = {
        'formula': 'ztrade_formula*.csv',
        '1h_part1': 'ztrade_export_1h_part1*.csv',
        '1h_part2': 'ztrade_export_1h_part2*.csv',
        '4h_part1': 'ztrade_export_4h_part1*.csv',
        '4h_part2': 'ztrade_export_4h_part2*.csv',
        '1d_part1': 'ztrade_export_1d_part1*.csv',
        '1d_part2': 'ztrade_export_1d_part2*.csv',
        '1w_part1': 'ztrade_export_1w_part1*.csv',
        '1w_part2': 'ztrade_export_1w_part2*.csv',
    }
    
    for key, pat in patterns.items():
        matched = glob.glob(os.path.join(dir_path, pat))
        if matched:
            matched.sort(key=os.path.getmtime, reverse=True)
            files[key] = matched[0]
            
    return files

def load_and_combine(part1_path, part2_path):
    if not part1_path and not part2_path:
        return pd.DataFrame()
    
    path = part1_path or part2_path
    if not part1_path or not part2_path:
        if os.path.exists(path):
            try:
                return pd.read_csv(path, comment='#')
            except Exception:
                return pd.DataFrame()
        return pd.DataFrame()
        
    try:
        df1 = pd.read_csv(part1_path, comment='#')
    except Exception:
        df1 = pd.DataFrame()
        
    try:
        df2 = pd.read_csv(part2_path, comment='#')
    except Exception:
        df2 = pd.DataFrame()
        
    if df1.empty:
        return df2
    if df2.empty:
        return df1
    return pd.concat([df1, df2], ignore_index=True)

def main():
    args = parse_args()
    dir_path = args.dir
    
    # 1. Locate files
    files = find_latest_exports(dir_path)
    
    # 2. Extract news
    news_text = ""
    formula_path = files['formula']
    if formula_path and os.path.exists(formula_path):
        try:
            df_formula = pd.read_csv(formula_path)
            if 'Section' in df_formula.columns and 'Value' in df_formula.columns:
                news_df = df_formula[df_formula['Section'] == 'LATEST_FINANCIAL_NEWS']
                news_list = news_df['Value'].dropna().astype(str).tolist()
                news_text = "\n".join(news_list)
        except Exception as e:
            print(f"Warning: Failed to parse news from formula: {e}", file=sys.stderr)
            
    # Initialize output dict
    out = {
        "news": news_text,
        "traps": [],
        "kill": [],
        "watch": [],
        "error": None
    }
    
    # 3. Load timeframes
    try:
        df_1h_raw = load_and_combine(files['1h_part1'], files['1h_part2'])
        df_4h_raw = load_and_combine(files['4h_part1'], files['4h_part2'])
        df_1d_raw = load_and_combine(files['1d_part1'], files['1d_part2'])
        df_1w_raw = load_and_combine(files['1w_part1'], files['1w_part2'])
    except Exception as e:
        out["error"] = f"Failed to load export CSVs: {str(e)}"
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    # Check for missing timeframes (execution fallback check)
    missing_tf = []
    if df_1h_raw.empty: missing_tf.append("1H")
    if df_4h_raw.empty: missing_tf.append("4H")
    if df_1d_raw.empty: missing_tf.append("1D")
    if df_1w_raw.empty: missing_tf.append("1W")
    
    if missing_tf:
        out["warning"] = f"Missing timeframes: {', '.join(missing_tf)}. Confluence analysis is limited."

    # Process 1H sequence data (for Rule 6 traps)
    df_1h_latest = pd.DataFrame()
    if not df_1h_raw.empty:
        try:
            # Sort to ensure proper shift sequence
            df_1h_sorted = df_1h_raw.sort_values(by=['Symbol', 'Datetime'])
            # Shift 1 to get previous candle data per symbol
            df_1h_sorted['Prev_IPI_Status'] = df_1h_sorted.groupby('Symbol')['IPI_Status'].shift(1)
            df_1h_sorted['Prev_RVOL'] = df_1h_sorted.groupby('Symbol')['RVOL'].shift(1)
            # Keep latest bar only
            df_1h_latest = df_1h_sorted.drop_duplicates(subset=['Symbol'], keep='last').copy()
        except Exception as e:
            print(f"Warning: Failed processing 1H sequence: {e}", file=sys.stderr)
            df_1h_latest = df_1h_raw.drop_duplicates(subset=['Symbol'], keep='last').copy()

    # Process other timeframes (latest row only)
    df_4h_latest = df_4h_raw.drop_duplicates(subset=['Symbol'], keep='last').copy() if not df_4h_raw.empty else pd.DataFrame()
    df_1d_latest = df_1d_raw.drop_duplicates(subset=['Symbol'], keep='last').copy() if not df_1d_raw.empty else pd.DataFrame()
    df_1w_latest = df_1w_raw.drop_duplicates(subset=['Symbol'], keep='last').copy() if not df_1w_raw.empty else pd.DataFrame()

    # Build unique list of symbols
    all_symbols = set()
    for df in [df_1h_latest, df_4h_latest, df_1d_latest, df_1w_latest]:
        if not df.empty and 'Symbol' in df.columns:
            all_symbols.update(df['Symbol'].dropna().tolist())
            
    if not all_symbols:
        # Return empty lists if no symbols exist
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    df_merged = pd.DataFrame({'Symbol': list(all_symbols)})

    # Merge 1H
    if not df_1h_latest.empty:
        cols_to_use = [c for c in ['Symbol', 'CMF', 'IPI_Status', 'Prev_RVOL', 'Prev_IPI_Status', 'RVOL'] if c in df_1h_latest.columns]
        df_merged = df_merged.merge(df_1h_latest[cols_to_use], on='Symbol', how='left')

    # Merge 1D
    if not df_1d_latest.empty:
        df_1d_renamed = df_1d_latest[['Symbol', 'Ema_Stack']].rename(columns={'Ema_Stack': '1D_Trend'})
        df_merged = df_merged.merge(df_1d_renamed, on='Symbol', how='left')

    # Handle Graceful Degradation: If 1H is missing but 1D is available, use 1D's data
    is_graceful_1d = False
    if df_1h_latest.empty and not df_1d_latest.empty:
        is_graceful_1d = True
        df_merged['CMF'] = df_1d_latest['CMF']
        df_merged['IPI_Status'] = df_1d_latest['IPI_Status']
        # If Prev keys are not present, initialize them
        df_merged['Prev_RVOL'] = 0.0
        df_merged['Prev_IPI_Status'] = 'unknown'

    # 4. Data Cleaning & Row-by-Row Fallback Notification
    df_merged['Fallback_Note'] = ''

    # CMF Fallback
    if 'CMF' not in df_merged.columns:
        df_merged['CMF'] = 0.0
        df_merged['Fallback_Note'] += 'Missing 1H_CMF Column; '
    else:
        mask_cmf = df_merged['CMF'].isna()
        df_merged.loc[mask_cmf, 'CMF'] = 0.0
        df_merged.loc[mask_cmf, 'Fallback_Note'] += 'Filled NaN CMF; '

    # 1D Trend (Ema_Stack) Fallback
    if '1D_Trend' not in df_merged.columns:
        df_merged['1D_Trend'] = 'unknown'
        df_merged['Fallback_Note'] += 'Missing 1D_Trend Column; '
    else:
        mask_trend = df_merged['1D_Trend'].isna()
        df_merged.loc[mask_trend, '1D_Trend'] = 'unknown'
        df_merged.loc[mask_trend, 'Fallback_Note'] += 'Missing 1D Data; '

    # IPI Status Fallback
    if 'IPI_Status' not in df_merged.columns:
        df_merged['IPI_Status'] = 'unknown'
        df_merged['Fallback_Note'] += 'Missing IPI_Status Column; '
    else:
        mask_ipi = df_merged['IPI_Status'].isna()
        df_merged.loc[mask_ipi, 'IPI_Status'] = 'unknown'
        df_merged.loc[mask_ipi, 'Fallback_Note'] += 'Filled NaN IPI; '

    # Sequence indicators check
    if 'Prev_RVOL' not in df_merged.columns:
        df_merged['Prev_RVOL'] = 0.0
    else:
        df_merged['Prev_RVOL'] = df_merged['Prev_RVOL'].fillna(0.0)

    if 'Prev_IPI_Status' not in df_merged.columns:
        df_merged['Prev_IPI_Status'] = 'unknown'
    else:
        df_merged['Prev_IPI_Status'] = df_merged['Prev_IPI_Status'].fillna('unknown')

    # Finalize Fallback Notes
    if is_graceful_1d:
        df_merged['Fallback_Note'] = 'Using 1D as active TF (1H missing)'
    else:
        df_merged['Fallback_Note'] = df_merged['Fallback_Note'].str.strip('; ')
        df_merged.loc[df_merged['Fallback_Note'] == '', 'Fallback_Note'] = 'None'

    # Map Ema_Stack for output dictionaries to ensure compatibility
    df_merged['Ema_Stack'] = df_merged['1D_Trend']

    # 5. Filter Rules (Traps, Kill, Watch)
    
    # Traps (Rule 6: sequence check)
    trap_mask = (
        (df_merged['1D_Trend'] == 'bull') &
        (df_merged['CMF'] > 0) &
        (df_merged['IPI_Status'].str.contains('distrib|neutral', case=False, na=False)) &
        (df_merged['Prev_RVOL'] > 1.2) &
        (df_merged['Prev_IPI_Status'].str.contains('accum', case=False, na=False))
    )
    traps_df = df_merged[trap_mask]
    
    # Kill (1D Bear Trend)
    kill_mask = (df_merged['1D_Trend'] == 'bear')
    kill_df = df_merged[kill_mask]
    
    # Watch (1D Bull Trend + positive CMF + current Accumulation)
    watch_mask = (
        (df_merged['1D_Trend'] == 'bull') &
        (df_merged['CMF'] > 0) &
        (df_merged['IPI_Status'].str.contains('accum', case=False, na=False)) &
        (~trap_mask) # Exclude traps to prevent duplicate classification
    )
    watch_df = df_merged[watch_mask]

    # Convert to JSON lists
    cols_to_export = ['Symbol', 'CMF', 'IPI_Status', '1D_Trend', 'Ema_Stack', 'Fallback_Note']
    
    out['traps'] = traps_df[cols_to_export].head(5).to_dict('records')
    out['kill'] = kill_df[cols_to_export].head(5).to_dict('records')
    out['watch'] = watch_df[cols_to_export].head(5).to_dict('records')

    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
