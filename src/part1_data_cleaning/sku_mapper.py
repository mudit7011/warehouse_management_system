import pandas as pd
import json
import logging
from datetime import datetime
import re
from typing import Dict, Any, Optional, List
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sku_mapping.log'),
        logging.StreamHandler()
    ]
)

class IntelligentSKUMapper:
    def __init__(self):
        self.master_mappings = {}
        self.processed_data = None
        self.auto_generated_mappings = {}
        
    def load_master_mappings(self, file_path=None):
        """Load master SKU mappings from file or create intelligent defaults"""
        try:
            if file_path:
                with open(file_path, 'r') as f:
                    self.master_mappings = json.load(f)
            else:
                self.master_mappings = {}
            logging.info(f"Loaded {len(self.master_mappings)} predefined mappings")
            return True
        except Exception as e:
            logging.error(f"Error loading mappings: {str(e)}")
            self.master_mappings = {}
            return True
    
    def analyze_sku_patterns(self, sku_list: List[str]) -> Dict[str, List[str]]:
        """Automatically analyze SKU patterns and create intelligent groupings"""
        pattern_groups = {}
        
        for sku in sku_list:
            if pd.isna(sku) or not str(sku).strip():
                continue
                
            sku = str(sku).strip()
            category = self._categorize_sku(sku)
            
            if category not in pattern_groups:
                pattern_groups[category] = []
            pattern_groups[category].append(sku)
        
        intelligent_mappings = {}
        for category, skus in pattern_groups.items():
            if len(skus) >= 1:
                intelligent_mappings[category] = list(set(skus))  # Remove duplicates
        
        return intelligent_mappings
    
    def _categorize_sku(self, sku: str) -> str:
        """Intelligently categorize a SKU based on its characteristics"""
        sku_upper = sku.upper()
        
        if any(brand in sku_upper for brand in ['FUSKED', 'DRAGON', 'RUDRAV', 'CSTE']):
            if 'FUSKED' in sku_upper:
                return 'FUSKED_BRAND_PRODUCTS'
            elif 'DRAGON' in sku_upper:
                return 'DRAGON_BRAND_PRODUCTS'
            elif 'RUDRAV' in sku_upper:
                return 'RUDRAV_BRAND_PRODUCTS'
            elif 'CSTE' in sku_upper:
                return 'CSTE_BRAND_PRODUCTS'
        
        if any(term in sku_upper for term in ['SUNGLASS', 'GLASSES']):
            return 'SUNGLASSES_CATEGORY'
        elif any(term in sku_upper for term in ['MUSIC', 'HEIST', 'SONG']):
            return 'ENTERTAINMENT_PRODUCTS'
        elif any(term in sku_upper for term in ['PACK OF', 'FREE SIZE']):
            return 'APPAREL_ACCESSORIES'
        elif any(term in sku_upper for term in ['WOODEN', 'CANVAS', 'CRAFT']):
            return 'HANDICRAFT_PRODUCTS'
        
        if sku.isdigit():
            length = len(sku)
            if length >= 15:
                prefix = sku[:3]
                return f'NUMERIC_ORDER_TYPE_{prefix}'
            elif length == 4:
                return f'HSN_CODE_{sku}'
            elif length >= 8:
                prefix = sku[:2]
                return f'NUMERIC_PRODUCT_TYPE_{prefix}'
        
        elif re.match(r'^[A-Z]{2,}[0-9]+', sku):
            prefix = re.match(r'^[A-Z]{2,}', sku).group()
            return f'ALPHANUMERIC_TYPE_{prefix}'
        
        elif re.match(r'^[A-Z0-9]{8,}$', sku) and any(c.isalpha() for c in sku):
            if sku.startswith(('ST', 'MT', 'MY')):
                prefix = sku[:2]
                return f'ELECTRONICS_TYPE_{prefix}'
            else:
                return 'MIXED_ALPHANUMERIC_PRODUCTS'
        
        elif len(sku) == 36 and sku.count('-') == 4:
            return 'UUID_SHIPMENT_IDS'
        elif len(sku) >= 20 and '-' in sku:
            return 'SYSTEM_GENERATED_IDS'
        
        elif len(sku) <= 10:
            if sku.isalnum():
                return 'SHORT_PRODUCT_CODES'
            else:
                return 'SHORT_MIXED_CODES'
        else:
            return 'LONG_IDENTIFIER_CODES'
    
    def auto_map_sku_to_msku(self, sku) -> str:
        """Automatically map SKU to Master SKU with intelligent categorization"""
        if pd.isna(sku) or sku is None:
            return "UNCATEGORIZED_UNKNOWN"
        
        sku = str(sku).strip()
        
        if not sku:
            return "UNCATEGORIZED_EMPTY"
        
        for msku, sku_variants in self.master_mappings.items():
            if sku in sku_variants or sku == msku:
                return msku
        
        category = self._categorize_sku(sku)
        
        if category not in self.auto_generated_mappings:
            self.auto_generated_mappings[category] = []
        if sku not in self.auto_generated_mappings[category]:
            self.auto_generated_mappings[category].append(sku)
        
        return category
    
    def process_sales_data(self, df):
        """Process sales data with intelligent auto-mapping"""
        try:
            processed_df = df.copy()
            
            sku_column = self._find_sku_column(df)
            
            if not sku_column:
                sku_column = df.columns[0]
                logging.warning(f"No clear SKU column found, using {sku_column}")
            
            logging.info(f"Using column '{sku_column}' as SKU column")
            
            unique_skus = df[sku_column].dropna().unique().tolist()
            
            intelligent_mappings = self.analyze_sku_patterns(unique_skus)
            
            self.master_mappings.update(intelligent_mappings)
            
            logging.info(f"Generated {len(intelligent_mappings)} intelligent mapping categories")
            for category, skus in intelligent_mappings.items():
                logging.info(f"  {category}: {len(skus)} SKUs")
            
            processed_df['MSKU'] = processed_df[sku_column].apply(self.auto_map_sku_to_msku)
            
            processed_df['processed_at'] = datetime.now()
            processed_df['mapping_method'] = 'intelligent_auto'
            
            self.processed_data = processed_df
            
            total_records = len(processed_df)
            mapped_records = len(processed_df[~processed_df['MSKU'].str.startswith('UNCATEGORIZED_', na=False)])
            success_rate = (mapped_records / total_records * 100) if total_records > 0 else 0
            
            logging.info(f"Processed {total_records} records with {success_rate:.1f}% success rate")
            
            return processed_df
            
        except Exception as e:
            logging.error(f"Error processing sales data: {str(e)}")
            raise

    def _find_sku_column(self, df) -> Optional[str]:
        """Intelligently find the SKU column in the dataframe"""
        sku_indicators = [
            ['sku', 'stock_keeping_unit'],
            ['product_id', 'product_code', 'item_id', 'item_code'],
            ['order_item_id', 'orderitem', 'order_id'],
            ['product', 'item', 'part'],
            ['code', 'id']
        ]
        
        columns_lower = [col.lower() for col in df.columns]
        
        for indicator_group in sku_indicators:
            for indicator in indicator_group:
                for i, col_lower in enumerate(columns_lower):
                    if indicator in col_lower:
                        return df.columns[i]
        
        for column in df.columns:
            sample_values = df[column].dropna().head(10)
            if len(sample_values) > 0:
                sku_like_count = 0
                for value in sample_values:
                    str_value = str(value).strip()
                    if (len(str_value) >= 3 and 
                        (str_value.isalnum() or 
                         any(c.isalnum() for c in str_value)) and
                        not str_value.replace('.', '').isdigit()): 
                        sku_like_count += 1
                
                if sku_like_count >= len(sample_values) * 0.7:
                    return column
        
        return None
    
    def get_mapping_summary(self) -> Dict[str, Any]:
        """Get a summary of all mappings created"""
        total_mappings = len(self.master_mappings)
        auto_generated = len(self.auto_generated_mappings)
        
        summary = {
            'total_categories': total_mappings,
            'auto_generated_categories': auto_generated,
            'predefined_categories': total_mappings - auto_generated,
            'category_details': {}
        }
        
        for category, skus in self.master_mappings.items():
            summary['category_details'][category] = {
                'sku_count': len(skus),
                'sample_skus': skus[:3] if len(skus) > 3 else skus,
                'is_auto_generated': category in self.auto_generated_mappings
            }
        
        return summary

SKUMapper = IntelligentSKUMapper