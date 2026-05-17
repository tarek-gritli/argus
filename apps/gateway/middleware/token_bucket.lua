-- Token bucket rate limiter.
-- KEYS[1]  = hash key "tb:{installation_id}"
-- ARGV[1]  = capacity  (max tokens)
-- ARGV[2]  = rate      (tokens refilled per second)
-- ARGV[3]  = ttl       (Redis key TTL in seconds)
-- Returns {1, remaining} if the request is allowed, {0, 0} if rejected.

local key      = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate     = tonumber(ARGV[2])
local ttl      = tonumber(ARGV[3])

-- Use Redis server time for sub-second precision and cross-instance consistency.
local t   = redis.call("TIME")
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000

local data        = redis.call("HMGET", key, "tokens", "last_refill")
local tokens      = tonumber(data[1]) or capacity
local last_refill = tonumber(data[2]) or now

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * rate)

if tokens < 1 then
    return {0, 0}
end

tokens = tokens - 1
redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
redis.call("EXPIRE", key, ttl)
return {1, math.floor(tokens)}
