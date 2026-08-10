package com.nba.predict.dto;

import java.time.LocalDate;

/**
 * 球员信息 DTO（避免直接暴露 Entity）
 */
public record PlayerDTO(
    Long playerId,
    String playerName,
    String playerNameEn,
    String position,
    Integer jerseyNumber,
    Long teamId,
    Integer age,
    Double height,
    Double weight,
    Integer draftYear,
    Integer experience,
    Integer allStarCount,
    String playerType,
    Integer clusterId,
    String clusterName,
    String injuryStatus
) {}
