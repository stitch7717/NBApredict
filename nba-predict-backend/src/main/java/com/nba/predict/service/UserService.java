package com.nba.predict.service;

import com.nba.predict.dto.AuthRequest;
import com.nba.predict.dto.AuthResponse;
import com.nba.predict.entity.User;

public interface UserService {

    /** 注册普通用户，成功后直接返回登录态 */
    AuthResponse register(AuthRequest request);

    /** 登录。request.role 非空时校验账号类型是否匹配 */
    AuthResponse login(AuthRequest request);

    User getByUsername(String username);

    User getById(Long userId);
}
