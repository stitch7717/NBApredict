package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.SeriesStar;
import com.nba.predict.mapper.SeriesStarMapper;
import com.nba.predict.service.SeriesStarService;
import com.nba.predict.util.HttpUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class SeriesStarServiceImpl implements SeriesStarService {

    private final SeriesStarMapper seriesStarMapper;
    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;

    @Override
    public Page<SeriesStar> listStars(int page, int size, Long teamId, String season) {
        Page<SeriesStar> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<SeriesStar> wrapper = new LambdaQueryWrapper<>();

        if (teamId != null) {
            wrapper.eq(SeriesStar::getTeamId, teamId);
        }
        if (StringUtils.hasText(season)) {
            wrapper.eq(SeriesStar::getSeason, season);
        }
        wrapper.eq(SeriesStar::getIsStar, 1);
        wrapper.orderByDesc(SeriesStar::getScoreUp);

        return seriesStarMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public SeriesStar getStarDetail(Long starId) {
        return seriesStarMapper.selectById(starId);
    }

    @Override
    public Object getSeasonReview(int page, int size, String season, Long teamId) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("page", page);
            request.put("size", size);
            if (StringUtils.hasText(season)) {
                request.put("season", season);
            }
            if (teamId != null) {
                request.put("team_id", teamId);
            }

            String response = httpUtil.get("/algorithm/series/review", null);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("获取赛季复盘数据失败: {}", e.getMessage());
            // 降级返回数据库数据
            Page<SeriesStar> pageParam = new Page<>(page, size);
            LambdaQueryWrapper<SeriesStar> wrapper = new LambdaQueryWrapper<>();
            if (StringUtils.hasText(season)) {
                wrapper.eq(SeriesStar::getSeason, season);
            }
            if (teamId != null) {
                wrapper.eq(SeriesStar::getTeamId, teamId);
            }
            wrapper.orderByDesc(SeriesStar::getCreateTime);
            return seriesStarMapper.selectPage(pageParam, wrapper);
        }
    }
}
