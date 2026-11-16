package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 系统用户
 */
@Data
@TableName("sys_user")
public class User {

    @TableId(type = IdType.AUTO)
    private Long userId;

    private String username;

    /** BCrypt 哈希。禁止序列化到响应体 */
    @JsonIgnore
    private String passwordHash;

    private String nickname;

    private String avatar;

    /** ADMIN | USER */
    private String role;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}
