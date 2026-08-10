package com.nba.predict.dto;

/**
 * 球队预测请求 DTO
 */
public record TeamPredictRequest(
    Long homeTeamId,
    Long awayTeamId,
    String scene,
    Boolean useOdds
) {}
