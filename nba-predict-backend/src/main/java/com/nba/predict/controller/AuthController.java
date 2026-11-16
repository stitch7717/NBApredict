package com.nba.predict.controller;

import com.nba.predict.common.Result;
import com.nba.predict.dto.AuthRequest;
import com.nba.predict.dto.AuthResponse;
import com.nba.predict.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "认证接口")
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    @Operation(summary = "注册普通用户")
    @PostMapping("/register")
    public Result<AuthResponse> register(@Valid @RequestBody AuthRequest request) {
        return Result.success("注册成功", userService.register(request));
    }

    @Operation(summary = "登录")
    @PostMapping("/login")
    public Result<AuthResponse> login(@Valid @RequestBody AuthRequest request) {
        return Result.success("登录成功", userService.login(request));
    }
}
