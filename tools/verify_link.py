#!/usr/bin/env python3
"""Verify one exact listing: python3 tools/verify_link.py LISTING_URL PRODUCT_URL"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from safeweb import verify
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('listing_url'); p.add_argument('product_url'); p.add_argument('--output',type=Path)
a=p.parse_args(); result=verify(a.listing_url,a.product_url)
text=json.dumps(result,indent=2,ensure_ascii=False)
if a.output: a.output.write_text(text+'\n')
print(text)
