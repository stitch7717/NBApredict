package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("odds_data")
public class OddsData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long gameId;

    private LocalDate gameDate;

    private Long homeTeamId;

    private Long awayTeamId;

    private Long sourceId;

    private BigDecimal homeWinOdds;

    private BigDecimal awayWinOdds;

    private BigDecimal homeWinProb;

    private BigDecimal awayWinProb;

    private BigDecimal handicapLine;

    private BigDecimal handicapHomeOdds;

    private BigDecimal handicapAwayOdds;

    private BigDecimal totalLine;

    private BigDecimal overOdds;

    private BigDecimal underOdds;

    private BigDecimal homeWinCoeff;

    private BigDecimal awayWinCoeff;

    private BigDecimal totalCoeff;

    private BigDecimal diffCoeff;

    private String dataQuality;

    private LocalDateTime collectTime;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
