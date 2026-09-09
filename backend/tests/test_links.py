from app.links import detect_platform, extract_product_id

def test_detect_platform_normal_flipkart():
    url = "https://www.flipkart.com/maggi-2-minute-masala-noodles-vegetarian/p/itm0a2ed56502396?marketplace=FLIPKART"
    assert detect_platform(url) == "flipkart"

def test_detect_platform_flipkart_minutes():
    url = "https://www.flipkart.com/maggi-2-minute-masala-noodles-vegetarian/p/itm0a2ed56502396?marketplace=HYPERLOCAL"
    assert detect_platform(url) == "flipkart_minutes"

def test_detect_platform_flipkart_minutes_extra_params():
    url = "https://www.flipkart.com/maggi-2-minute-masala-noodles-vegetarian/p/itm0a2ed56502396?foo=bar&marketplace=HYPERLOCAL&baz=qux"
    assert detect_platform(url) == "flipkart_minutes"

def test_detect_platform_flipkart_no_marketplace():
    url = "https://www.flipkart.com/maggi-2-minute-masala-noodles-vegetarian/p/itm0a2ed56502396"
    assert detect_platform(url) == "flipkart"

def test_detect_platform_flipkart_short_url():
    url = "https://dl.flipkart.com/s/abcdefgh"
    assert detect_platform(url) == "flipkart"

def test_detect_platform_invalid_flipkart():
    url = "https://www.flipkart.com/something"
    assert detect_platform(url) == "flipkart"
    # Although platform is flipkart, product ID extraction should fail
    platform, pid = extract_product_id(url)
    assert platform == "flipkart"
    assert pid is None

def test_extract_product_id_flipkart():
    url = "https://www.flipkart.com/maggi/p/itm0a2ed56502396?marketplace=HYPERLOCAL"
    platform, pid = extract_product_id(url)
    assert platform == "flipkart_minutes"
    assert pid == "itm0a2ed56502396"
