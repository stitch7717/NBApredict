package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.Team;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.TeamMapper;
import com.nba.predict.service.TeamService;
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
public class TeamServiceImpl implements TeamService {

    private final TeamMapper teamMapper;
    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;

    @Override
    public Page<Team> listTeams(int page, int size, String conference, String defenseType, String offenseType) {
        Page<Team> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Team> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(conference)) {
            wrapper.eq(Team::getConference, conference);
        }
        if (StringUtils.hasText(defenseType)) {
            wrapper.eq(Team::getDefenseType, defenseType);
        }
        if (StringUtils.hasText(offenseType)) {
            wrapper.eq(Team::getOffenseType, offenseType);
        }
        wrapper.eq(Team::getStatus, 1);
        wrapper.orderByAsc(Team::getTeamId);

        return teamMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public Team getTeamDetail(Long teamId) {
        Team team = teamMapper.selectById(teamId);
        if (team == null) {
            throw new BusinessException(ResultCode.TEAM_NOT_FOUND);
        }
        return team;
    }

    @Override
    public Object predict(Long homeTeamId, Long awayTeamId, String scene, boolean useOdds) {
        // 校验球队存在
        Team homeTeam = teamMapper.selectById(homeTeamId);
        Team awayTeam = teamMapper.selectById(awayTeamId);
        if (homeTeam == null || awayTeam == null) {
            throw new BusinessException(ResultCode.TEAM_NOT_FOUND);
        }

        // 调用算法层
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("home_team_id", homeTeamId);
            request.put("away_team_id", awayTeamId);
            request.put("scene", scene);
            request.put("use_odds", useOdds);

            String response = httpUtil.post("/algorithm/team/predict", request);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("算法调用失败: {}", e.getMessage());
            return buildDegradedResult(homeTeam, awayTeam, scene);
        }
    }

    private Map<String, Object> buildDegradedResult(Team homeTeam, Team awayTeam, String scene) {
        Map<String, Object> result = new HashMap<>();
        result.put("home_team_id", homeTeam.getTeamId());
        result.put("home_team_name", homeTeam.getTeamName());
        result.put("away_team_id", awayTeam.getTeamId());
        result.put("away_team_name", awayTeam.getTeamName());
        result.put("scene", scene);
        result.put("degraded", true);
        result.put("message", "算法服务暂时不可用，返回降级数据");
        return result;
    }
}
