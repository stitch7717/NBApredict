package com.nba.predict.common;

public final class AppConstants {
    private AppConstants() {}

    public static final String DEFAULT_SEASON = "2025-26";
    public static final String SCENE_REGULAR = "常规赛";
    public static final String SCENE_PLAYOFFS = "季后赛";
    public static final String SCENE_KEY_GAME = "关键战";

    /** 用户角色 */
    public static final String ROLE_ADMIN = "ADMIN";
    public static final String ROLE_USER = "USER";

    public static final String ALGO_PLAYER_PREDICT = "/algorithm/player/predict";
    public static final String ALGO_TEAM_PREDICT = "/algorithm/team/predict";
    public static final String ALGO_ODDS_CONVERT = "/algorithm/odds/convert";
    public static final String ALGO_SERIES_REVIEW = "/algorithm/series/review";
}
