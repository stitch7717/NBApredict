package com.nba.predict.config;

import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.nba.predict.common.AppConstants;
import com.nba.predict.entity.User;
import com.nba.predict.mapper.UserMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * 预置两个演示账号（管理员 1 个、普通用户 1 个）。
 *
 * 仅在账号不存在时创建，启动多次不会重复插入。
 * 密码以 BCrypt 哈希入库，明文不落盘；可通过 app.default-* 配置覆盖。
 */
@Slf4j
@Component
@Order(1)
public class UserDataInitializer implements CommandLineRunner {

    private final UserMapper userMapper;
    private final String adminUsername;
    private final String adminPassword;
    private final String userUsername;
    private final String userPassword;

    public UserDataInitializer(UserMapper userMapper,
                               @Value("${app.default-admin.username:admin}") String adminUsername,
                               @Value("${app.default-admin.password:admin123}") String adminPassword,
                               @Value("${app.default-user.username:user}") String userUsername,
                               @Value("${app.default-user.password:user123}") String userPassword) {
        this.userMapper = userMapper;
        this.adminUsername = adminUsername;
        this.adminPassword = adminPassword;
        this.userUsername = userUsername;
        this.userPassword = userPassword;
    }

    @Override
    public void run(String... args) {
        seed(adminUsername, adminPassword, "管理员", AppConstants.ROLE_ADMIN);
        seed(userUsername, userPassword, "普通用户", AppConstants.ROLE_USER);
    }

    private void seed(String username, String rawPassword, String nickname, String role) {
        Long exists = userMapper.selectCount(
                Wrappers.<User>lambdaQuery().eq(User::getUsername, username));
        if (exists != null && exists > 0) {
            return;
        }
        User user = new User();
        user.setUsername(username);
        user.setPasswordHash(BCrypt.hashpw(rawPassword));
        user.setNickname(nickname);
        user.setRole(role);
        userMapper.insert(user);
        log.info("已创建预置账号: {} ({})", username, role);
    }
}
