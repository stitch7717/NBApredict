package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("player_data")
public class PlayerData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long playerId;

    private String season;

    private Long teamId;

    private Integer gamesPlayed;

    private Integer gamesStarted;

    private BigDecimal minutesPerGame;

    private BigDecimal pointsPerGame;

    private BigDecimal reboundsPerGame;

    private BigDecimal assistsPerGame;

    private BigDecimal stealsPerGame;

    private BigDecimal blocksPerGame;

    private BigDecimal turnoversPerGame;

    private BigDecimal fgMadePerGame;

    private BigDecimal fgAttemptedPerGame;

    private BigDecimal fgPercentage;

    private BigDecimal threeMadePerGame;

    private BigDecimal threeAttemptedPerGame;

    private BigDecimal threePercentage;

    private BigDecimal ftMadePerGame;

    private BigDecimal ftAttemptedPerGame;

    private BigDecimal ftPercentage;

    private BigDecimal per;

    private BigDecimal trueShootingPct;

    private BigDecimal usageRate;

    private BigDecimal winShares;

    private BigDecimal bpm;

    private BigDecimal vorp;

    private BigDecimal isolationPct;

    private BigDecimal pickRollPct;

    private BigDecimal spotUpPct;

    private BigDecimal postUpPct;

    private BigDecimal pointsStd;

    private BigDecimal pointsCv;

    private BigDecimal vsPgEfficiency;

    private BigDecimal vsSgEfficiency;

    private BigDecimal vsSfEfficiency;

    private BigDecimal vsPfEfficiency;

    private BigDecimal vsCEfficiency;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
