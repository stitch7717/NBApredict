package com.nba.predict.dto;

/**
 * 球队信息 DTO（避免直接暴露 Entity）
 */
public record TeamDTO(
    Long teamId,
    String teamName,
    String teamNameEn,
    String abbreviation,
    String conference,
    String division,
    String city,
    String arena,
    String defenseType,
    String offenseType,
    String strengthLevel,
    Double strengthScore,
    Double homeWinRate,
    Double awayWinRate
) {}
