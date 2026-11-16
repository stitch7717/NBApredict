package com.nba.predict.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * 登录 / 注册请求
 *
 * role 仅在登录时用于校验账号类型（管理员入口只接受 ADMIN 账号）；
 * 注册时后端强制为 USER，不读取该字段。
 */
public record AuthRequest(
        @NotBlank(message = "用户名不能为空")
        @Size(min = 3, max = 30, message = "用户名长度需在 3~30 之间")
        String username,

        @NotBlank(message = "密码不能为空")
        @Size(min = 6, max = 64, message = "密码长度需在 6~64 之间")
        String password,

        String nickname,

        /** ADMIN | USER，可为空 */
        String role
) {
}
