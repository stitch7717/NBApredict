package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.OddsData;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.OddsDataMapper;
import com.nba.predict.service.OddsService;
import com.nba.predict.util.HttpUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class OddsServiceImpl implements OddsService {

    private final OddsDataMapper oddsDataMapper;
    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;

    @Override
    public Page<OddsData> listOdds(int page, int size, Long homeTeamId, Long awayTeamId,
                                   LocalDate gameDate, Long sourceId) {
        Page<OddsData> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<OddsData> wrapper = new LambdaQueryWrapper<>();

        if (homeTeamId != null) {
            wrapper.eq(OddsData::getHomeTeamId, homeTeamId);
        }
        if (awayTeamId != null) {
            wrapper.eq(OddsData::getAwayTeamId, awayTeamId);
        }
        if (gameDate != null) {
            wrapper.eq(OddsData::getGameDate, gameDate);
        }
        if (sourceId != null) {
            wrapper.eq(OddsData::getSourceId, sourceId);
        }
        wrapper.orderByDesc(OddsData::getGameDate);

        return oddsDataMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public OddsData getOddsDetail(Long id) {
        OddsData odds = oddsDataMapper.selectById(id);
        if (odds == null) {
            throw new BusinessException(ResultCode.DATA_NOT_FOUND);
        }
        return odds;
    }

    @Override
    public Object convertOdds(Long oddsId) {
        OddsData odds = getOddsDetail(oddsId);
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("odds_id", oddsId);
            request.put("home_win_odds", odds.getHomeWinOdds());
            request.put("away_win_odds", odds.getAwayWinOdds());
            request.put("handicap_line", odds.getHandicapLine());
            request.put("total_line", odds.getTotalLine());

            String response = httpUtil.post("/algorithm/odds/calculate", request);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("赔率换算失败: {}", e.getMessage());
            throw new BusinessException(ResultCode.ALGORITHM_ERROR);
        }
    }

    @Override
    public Object collectOdds(Long sourceId, LocalDate startDate, LocalDate endDate) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("source_id", sourceId);
            request.put("start_date", startDate.toString());
            request.put("end_date", endDate.toString());

            String response = httpUtil.post("/algorithm/odds/collect", request);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("赔率采集失败: {}", e.getMessage());
            throw new BusinessException(ResultCode.DATASOURCE_ERROR);
        }
    }

    @Override
    public Object backtestOdds(String season, Long sourceId) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("season", season);
            request.put("source_id", sourceId);

            String response = httpUtil.post("/algorithm/odds/backtest", request);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("赔率回测失败: {}", e.getMessage());
            throw new BusinessException(ResultCode.ALGORITHM_ERROR);
        }
    }
}
