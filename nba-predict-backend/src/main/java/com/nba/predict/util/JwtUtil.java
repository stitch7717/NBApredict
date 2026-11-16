package com.nba.predict.util;

import cn.hutool.jwt.JWT;
import cn.hutool.jwt.JWTUtil;
import cn.hutool.jwt.JWTValidator;
import com.nba.predict.entity.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * JWT 签发与校验。
 *
 * 密钥来自配置 app.jwt.secret，禁止硬编码在源码中。
 */
@Component
public class JwtUtil {

    private static final String CLAIM_USER_ID = "userId";
    private static final String CLAIM_USERNAME = "username";
    private static final String CLAIM_ROLE = "role";
    private static final String CLAIM_EXP = "exp";
    private static final String CLAIM_IAT = "iat";

    private final byte[] key;
    private final long expireMillis;

    public JwtUtil(@Value("${app.jwt.secret}") String secret,
                   @Value("${app.jwt.expire-hours:72}") long expireHours) {
        this.key = secret.getBytes(StandardCharsets.UTF_8);
        this.expireMillis = expireHours * 3600_000L;
    }

    public String create(User user) {
        long nowSeconds = System.currentTimeMillis() / 1000;
        return JWT.create()
                .setPayload(CLAIM_USER_ID, user.getUserId())
                .setPayload(CLAIM_USERNAME, user.getUsername())
                .setPayload(CLAIM_ROLE, user.getRole())
                .setPayload(CLAIM_IAT, nowSeconds)
                .setPayload(CLAIM_EXP, nowSeconds + expireMillis / 1000)
                .setKey(key)
                .sign();
    }

    /**
     * 校验并解析 token。签名错误或已过期时返回 null，调用方据此判定未授权。
     */
    public Map<String, Object> parse(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        try {
            JWT jwt = JWTUtil.parseToken(token);
            if (!jwt.setKey(key).verify()) {
                return null;
            }
            JWTValidator.of(jwt).validateDate();
            return jwt.getPayloads();
        } catch (Exception e) {
            return null;
        }
    }

    public Long userIdOf(String token) {
        Map<String, Object> payload = parse(token);
        if (payload == null) {
            return null;
        }
        Object value = payload.get(CLAIM_USER_ID);
        return value instanceof Number n ? n.longValue() : null;
    }

    public String roleOf(String token) {
        Map<String, Object> payload = parse(token);
        return payload == null ? null : String.valueOf(payload.get(CLAIM_ROLE));
    }
}
