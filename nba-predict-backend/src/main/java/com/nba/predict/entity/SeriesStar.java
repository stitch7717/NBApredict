package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("series_star")
public class SeriesStar {

    @TableId(type = IdType.AUTO)
    private Long starId;

    private Long seriesId;

    private Long playerId;

    private Long teamId;

    private Long opponentTeamId;

    private String season;

    private BigDecimal avgScore;

    private BigDecimal avgFgPct;

    private BigDecimal scoreUp;

    private BigDecimal hitRateUp;

    private BigDecimal judgeThresholdScore;

    private BigDecimal judgeThresholdPct;

    private Integer isStar;

    private Long keyGameId;

    private Integer keyGameScore;

    private BigDecimal keyGameFgPct;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
