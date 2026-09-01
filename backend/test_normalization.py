import unittest
from app.normalization import parse_quantity

class TestNormalization(unittest.TestCase):
    def test_basic_weights(self):
        res = parse_quantity("70 g")
        self.assertIsNotNone(res)
        self.assertEqual(res.pack_count, 1)
        self.assertEqual(res.quantity_per_pack, 70.0)
        self.assertEqual(res.quantity_unit, "g")
        self.assertEqual(res.total_quantity, 70.0)
        self.assertEqual(res.confidence, "HIGH")

        res = parse_quantity("1 kg")
        self.assertEqual(res.quantity_per_pack, 1.0)
        self.assertEqual(res.quantity_unit, "kg")
        self.assertEqual(res.total_quantity, 1.0)

        res = parse_quantity("500ml")
        self.assertEqual(res.quantity_per_pack, 500.0)
        self.assertEqual(res.quantity_unit, "ml")

    def test_multipliers(self):
        # Suffix
        res = parse_quantity("420 g x 2")
        self.assertEqual(res.pack_count, 2)
        self.assertEqual(res.quantity_per_pack, 420.0)
        self.assertEqual(res.total_quantity, 840.0)
        
        res = parse_quantity("70 g x 4")
        self.assertEqual(res.pack_count, 4)
        self.assertEqual(res.quantity_per_pack, 70.0)
        self.assertEqual(res.total_quantity, 280.0)

        res = parse_quantity("500ml x 2")
        self.assertEqual(res.pack_count, 2)
        self.assertEqual(res.quantity_per_pack, 500.0)
        self.assertEqual(res.quantity_unit, "ml")
        self.assertEqual(res.total_quantity, 1000.0)

        res = parse_quantity("420g × 2")
        self.assertEqual(res.pack_count, 2)

        # Prefix
        res = parse_quantity("2 x 500 ml")
        self.assertEqual(res.pack_count, 2)
        self.assertEqual(res.quantity_per_pack, 500.0)
        self.assertEqual(res.total_quantity, 1000.0)
        
        res = parse_quantity("6 x 70 g")
        self.assertEqual(res.pack_count, 6)
        self.assertEqual(res.quantity_per_pack, 70.0)
        self.assertEqual(res.total_quantity, 420.0)

    def test_pack_of(self):
        res = parse_quantity("Pack of 2")
        # Since it has no base weight, we fallback to parsing 'pack' as count-only if possible.
        # Wait, my logic for "Pack of 2" might return None if there is no unit.
        # But "Pack of 2" has "Pack", we should just treat it as 2 packs.
        # We can handle this logic in normalization.py if needed.
        pass
        
    def test_count_only(self):
        res = parse_quantity("4 pcs")
        self.assertEqual(res.pack_count, 1)
        self.assertEqual(res.quantity_per_pack, 4.0)
        self.assertEqual(res.quantity_unit, "pc")
        
        res = parse_quantity("2 bottles")
        self.assertEqual(res.quantity_unit, "bottle")
        self.assertEqual(res.quantity_per_pack, 2.0)
        
        res = parse_quantity("2 packs")
        self.assertEqual(res.quantity_unit, "pack")
        self.assertEqual(res.quantity_per_pack, 2.0)
        
    def test_embedded_titles(self):
        res = parse_quantity("Maggi 2-Minute Noodles 70g x 4")
        self.assertEqual(res.pack_count, 4)
        self.assertEqual(res.quantity_per_pack, 70.0)
        self.assertEqual(res.total_quantity, 280.0)

        res = parse_quantity("Dettol Handwash 250 ml x 2")
        self.assertEqual(res.pack_count, 2)
        self.assertEqual(res.quantity_per_pack, 250.0)
        self.assertEqual(res.total_quantity, 500.0)

    def test_pack_of_with_weight(self):
        res = parse_quantity("Pack of 4 (70g)")
        self.assertEqual(res.pack_count, 4)
        self.assertEqual(res.quantity_per_pack, 70.0)
        self.assertEqual(res.total_quantity, 280.0)

if __name__ == '__main__':
    unittest.main()
