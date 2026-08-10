package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.OddsData;

import java.time.LocalDate;

public interface OddsService {

    Page<OddsData> listOdds(int page, int size, Long homeTeamId, Long awayTeamId,
                            LocalDate gameDate, Long sourceId);

    OddsData getOddsDetail(Long id);

    Object convertOdds(Long oddsId);

    Object collectOdds(Long sourceId, LocalDate startDate, LocalDate endDate);

    Object backtestOdds(String season, Long sourceId);
}
