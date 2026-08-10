package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.Player;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.PlayerMapper;
import com.nba.predict.service.PlayerService;
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
public class PlayerServiceImpl implements PlayerService {

    private final PlayerMapper playerMapper;
    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;

    @Override
    public Page<Player> listPlayers(int page, int size, String keyword, String position, Integer teamId) {
        Page<Player> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<Player> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(keyword)) {
            wrapper.and(w -> w.like(Player::getPlayerName, keyword)
                    .or().like(Player::getPlayerNameEn, keyword));
        }
        if (StringUtils.hasText(position)) {
            wrapper.eq(Player::getPosition, position);
        }
        if (teamId != null) {
            wrapper.eq(Player::getTeamId, teamId);
        }
        wrapper.eq(Player::getStatus, 1);
        wrapper.orderByDesc(Player::getUpdateTime);

        return playerMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public Player getPlayerDetail(Long playerId) {
        Player player = playerMapper.selectById(playerId);
        if (player == null) {
            throw new BusinessException(ResultCode.PLAYER_NOT_FOUND);
        }
        return player;
    }

    @Override
    public Object predict(Long playerId, Long opponentPlayerId, String scene, String homeAway) {
        // 校验球员存在
        Player player = playerMapper.selectById(playerId);
        if (player == null) {
            throw new BusinessException(ResultCode.PLAYER_NOT_FOUND);
        }

        // 调用算法层
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("player_id", playerId);
            request.put("opponent_player_id", opponentPlayerId);
            request.put("scene", scene);
            request.put("home_away", homeAway);

            String response = httpUtil.post("/algorithm/player/predict", request);
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("算法调用失败: {}", e.getMessage());
            // 降级返回基础数据
            return buildDegradedResult(player, scene, homeAway);
        }
    }

    private Map<String, Object> buildDegradedResult(Player player, String scene, String homeAway) {
        Map<String, Object> result = new HashMap<>();
        result.put("player_id", player.getPlayerId());
        result.put("player_name", player.getPlayerName());
        result.put("scene", scene);
        result.put("points_low", 0);
        result.put("points_mid", 0);
        result.put("points_high", 0);
        result.put("fg_pct", 0);
        result.put("total_coeff", 1.0);
        result.put("degraded", true);
        result.put("message", "算法服务暂时不可用，返回降级数据");
        return result;
    }
}
