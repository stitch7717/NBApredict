package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("player_matchup")
public class PlayerMatchup {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long gameId;

    private LocalDate gameDate;

    private String season;

    private Long offensePlayerId;

    private Long offenseTeamId;

    private Integer offenseRank;

    private Long defensePlayerId;

    private Long defenseTeamId;

    private String positionDiff;

    private Integer matchupMinutes;

    private Integer offensePoints;

    private Integer offenseAttempts;

    private Integer offenseMade;

    private BigDecimal offenseEfficiency;

    private BigDecimal defenseEfficiency;

    private BigDecimal netEfficiency;

    private BigDecimal perScore;

    private BigDecimal tsScore;

    private BigDecimal usageScore;

    private BigDecimal compositeScore;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
