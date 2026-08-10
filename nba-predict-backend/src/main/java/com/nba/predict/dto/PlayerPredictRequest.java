package com.nba.predict.dto;

/**
 * 球员预测请求 DTO
 */
public record PlayerPredictRequest(
    Long playerId,
    Long opponentPlayerId,
    String scene,
    String homeAway
) {}
