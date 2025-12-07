from expiringdict import ExpiringDict

cache = ExpiringDict(max_len=100000, max_age_seconds=60*60*4)

def get_cache(key):
    return cache.get(key)

def set_cache(key, value):
    cache[key] = value