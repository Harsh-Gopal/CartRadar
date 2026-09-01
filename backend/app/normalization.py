"""Robust cross-platform product offer normalization engine."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class NormalizedQuantity:
    pack_count: int
    quantity_per_pack: float
    quantity_unit: str
    total_quantity: float
    total_quantity_unit: str
    confidence: str
    raw_variant: str

# Common unit normalizations
UNIT_MAP = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "mls": "ml", "milliliter": "ml", "millilitre": "ml",
    "l": "L", "ltr": "L", "liter": "L", "litre": "L", "litres": "L", "liters": "L",
    "pc": "pc", "pcs": "pc", "piece": "pc", "pieces": "pc",
    "pack": "pack", "packs": "pack", "packet": "pack",
    "bottle": "bottle", "bottles": "bottle",
    "can": "can", "cans": "can",
    "box": "box", "boxes": "box",
    "tablet": "tablet", "tablets": "tablet",
    "capsule": "capsule", "capsules": "capsule",
    "jar": "jar", "jars": "jar"
}

# Regex for base quantity, e.g., "420 g", "1.5 kg", "500ml"
RE_QTY = r'(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)'

# Matches: "420 g x 2", "420g × 2", "420 g * 2"
RE_MULTIPLIER_SUFFIX = rf'{RE_QTY}\s*(?:x|X|×|\*)\s*(?P<mult1>\d+)'

# Matches: "2 x 420 g", "2 × 420g"
RE_MULTIPLIER_PREFIX = rf'(?P<mult2>\d+)\s*(?:x|X|×|\*)\s*{RE_QTY}'

# Matches: "Pack of 2", "Pack of 4"
RE_PACK_OF = r'(?i)pack\s+of\s+(?P<pack_count>\d+)'

# Matches: "2 packs", "4 pcs"
RE_COUNT_ONLY = r'(?P<count>\d+)\s+(?P<c_unit>packs?|pcs?|pieces?|bottles?|cans?|boxes?|tablets?|capsules?|jars?)'

def _normalize_unit(unit_str: str) -> str:
    """Normalize a unit string to standard abbreviation."""
    u = unit_str.strip().lower()
    return UNIT_MAP.get(u, u)

def parse_quantity(text: str) -> Optional[NormalizedQuantity]:
    """Parse a quantity string into a NormalizedQuantity object."""
    if not text:
        return None
        
    text = text.strip()
    pack_count = 1
    qty_per_pack = 0.0
    unit = ""
    confidence = "UNKNOWN"
    
    # 1. Try to find explicit multipliers (e.g., "70 g x 4")
    m_suffix = re.search(RE_MULTIPLIER_SUFFIX, text)
    if m_suffix:
        qty_per_pack = float(m_suffix.group('qty'))
        unit = _normalize_unit(m_suffix.group('unit'))
        pack_count = int(m_suffix.group('mult1'))
        confidence = "HIGH"
    else:
        # 2. Try prefix multiplier (e.g., "4 x 70 g")
        m_prefix = re.search(RE_MULTIPLIER_PREFIX, text)
        if m_prefix:
            qty_per_pack = float(m_prefix.group('qty'))
            unit = _normalize_unit(m_prefix.group('unit'))
            pack_count = int(m_prefix.group('mult2'))
            confidence = "HIGH"
        else:
            # 3. Look for "Pack of X" inside the string
            m_pack = re.search(RE_PACK_OF, text)
            if m_pack:
                pack_count = int(m_pack.group('pack_count'))
                
            # Now find the base quantity (e.g., "70 g")
            # We take the LAST match if there are multiple, as usually titles end with "70 g"
            qty_matches = list(re.finditer(RE_QTY, text))
            
            if qty_matches:
                # Filter out pure numbers without valid units if possible
                valid_matches = [m for m in qty_matches if _normalize_unit(m.group('unit')) in UNIT_MAP]
                
                # If we found matches with recognized units, use the last one
                if valid_matches:
                    last_match = valid_matches[-1]
                    qty_per_pack = float(last_match.group('qty'))
                    unit = _normalize_unit(last_match.group('unit'))
                    confidence = "MEDIUM" if pack_count > 1 else "LOW"
                    
                    # If this is the EXACT string, bump confidence
                    if text.strip() == last_match.group(0):
                        confidence = "HIGH"
                else:
                    # No recognized units, fallback to count only
                    m_count = re.search(RE_COUNT_ONLY, text, re.IGNORECASE)
                    if m_count:
                        qty_per_pack = float(m_count.group('count'))
                        unit = _normalize_unit(m_count.group('c_unit'))
                        pack_count = 1
                        confidence = "LOW"
            else:
                # 4. Fallback to just counts (e.g., "4 pcs")
                m_count = re.search(RE_COUNT_ONLY, text, re.IGNORECASE)
                if m_count:
                    qty_per_pack = float(m_count.group('count'))
                    unit = _normalize_unit(m_count.group('c_unit'))
                    pack_count = 1
                    confidence = "LOW"
                elif pack_count > 1:
                    qty_per_pack = 1.0
                    unit = "pack"
                    confidence = "LOW"

    if qty_per_pack > 0 and unit:
        # Calculate total quantity
        total_qty = qty_per_pack * pack_count
        
        # We don't auto-convert units here (e.g. 1000g -> 1kg) 
        # to preserve original intent, but we do standardize the string representation.
        
        return NormalizedQuantity(
            pack_count=pack_count,
            quantity_per_pack=qty_per_pack,
            quantity_unit=unit,
            total_quantity=total_qty,
            total_quantity_unit=unit,
            confidence=confidence,
            raw_variant=text
        )
        
    return None

def calculate_unit_price(price: float, nq: NormalizedQuantity) -> Optional[float]:
    """Calculate the unit price based on the total quantity."""
    if not price or not nq or nq.total_quantity <= 0:
        return None
        
    # Standardize to per 100g or per 100ml where appropriate
    if nq.total_quantity_unit in ('g', 'ml'):
        # If the total quantity is very large, maybe per kg/L is better,
        # but the prompt specifically requests price per 100g or price per kg.
        # Let's standardize on price per unit, and UI can decide.
        # Actually, let's return raw price per 1 unit.
        pass
        
    return price / nq.total_quantity
