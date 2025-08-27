from expiringdict import ExpiringDict

cache = ExpiringDict(max_len=1000, max_age_seconds=60*60)

def get_cache(key):
    return cache.get(key)

def set_cache(key, value):
    cache[key] = value