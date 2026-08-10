package com.nba.predict.common;

import lombok.Getter;

/**
 * 响应状态码
 */
@Getter
public enum ResultCode {

    // 成功
    SUCCESS(200, "操作成功"),

    // 客户端错误 4xx
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未授权"),
    FORBIDDEN(403, "禁止访问"),
    NOT_FOUND(404, "资源不存在"),
    METHOD_NOT_ALLOWED(405, "请求方法不允许"),
    PARAM_ERROR(400, "参数校验失败"),

    // 服务端错误 5xx
    INTERNAL_ERROR(500, "服务器内部错误"),
    SERVICE_UNAVAILABLE(503, "服务不可用"),

    // 业务错误 1xxx
    PLAYER_NOT_FOUND(1001, "球员不存在"),
    TEAM_NOT_FOUND(1002, "球队不存在"),
    GAME_NOT_FOUND(1003, "比赛不存在"),
    ODDS_SOURCE_NOT_FOUND(1004, "数据源不存在"),
    PREDICT_FAILED(1005, "预测计算失败"),
    DATA_NOT_FOUND(1006, "数据不存在"),

    // 算法层错误 2xxx
    ALGORITHM_ERROR(2001, "算法调用失败"),
    ALGORITHM_TIMEOUT(2002, "算法调用超时"),
    ALGORITHM_DEGRADED(2003, "算法服务降级"),

    // 数据源错误 3xxx
    DATASOURCE_ERROR(3001, "数据源采集失败"),
    DATASOURCE_SWITCHED(3002, "数据源已自动切换");

    private final int code;
    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }
}
