package com.nba.predict.dto;

/**
 * 预测结果 DTO
 */
public record PredictResultDTO(
    String homeTeamName,
    String awayTeamName,
    Double homeScore,
    Double awayScore,
    Double homeWinProb,
    String predictedWinner,
    Object coefficients,
    String model,
    Object details
) {}
