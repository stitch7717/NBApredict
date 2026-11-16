package com.nba.predict.dto;

import com.nba.predict.entity.User;

/**
 * 登录成功后的返回体（不含密码哈希）
 */
public record AuthResponse(
        Long userId,
        String username,
        String nickname,
        String role,
        String token
) {
    public static AuthResponse of(User user, String token) {
        return new AuthResponse(
                user.getUserId(),
                user.getUsername(),
                user.getNickname() != null ? user.getNickname() : user.getUsername(),
                user.getRole(),
                token
        );
    }
}
