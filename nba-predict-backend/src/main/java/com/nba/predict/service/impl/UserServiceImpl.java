package com.nba.predict.service.impl;

import cn.hutool.core.util.StrUtil;
import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.nba.predict.common.AppConstants;
import com.nba.predict.common.ResultCode;
import com.nba.predict.dto.AuthRequest;
import com.nba.predict.dto.AuthResponse;
import com.nba.predict.entity.User;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.UserMapper;
import com.nba.predict.service.UserService;
import com.nba.predict.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    private final UserMapper userMapper;
    private final JwtUtil jwtUtil;

    @Override
    public AuthResponse register(AuthRequest request) {
        String username = request.username().trim();
        if (getByUsername(username) != null) {
            throw new BusinessException(ResultCode.USERNAME_EXISTS);
        }

        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(BCrypt.hashpw(request.password()));
        user.setNickname(StrUtil.isBlank(request.nickname()) ? username : request.nickname().trim());
        // 公开注册一律为普通用户，管理员账号只能由初始化器创建
        user.setRole(AppConstants.ROLE_USER);
        userMapper.insert(user);

        log.info("新用户注册: {}", username);
        return AuthResponse.of(user, jwtUtil.create(user));
    }

    @Override
    public AuthResponse login(AuthRequest request) {
        User user = getByUsername(request.username().trim());
        // 账号不存在与密码错误返回同一提示，避免账号枚举
        if (user == null || !BCrypt.checkpw(request.password(), user.getPasswordHash())) {
            throw new BusinessException(ResultCode.LOGIN_FAILED);
        }
        if (StrUtil.isNotBlank(request.role())
                && !request.role().equalsIgnoreCase(user.getRole())) {
            throw new BusinessException(ResultCode.ROLE_MISMATCH);
        }
        return AuthResponse.of(user, jwtUtil.create(user));
    }

    @Override
    public User getByUsername(String username) {
        if (StrUtil.isBlank(username)) {
            return null;
        }
        return userMapper.selectOne(
                Wrappers.<User>lambdaQuery().eq(User::getUsername, username.trim()));
    }

    @Override
    public User getById(Long userId) {
        return userId == null ? null : userMapper.selectById(userId);
    }
}
