package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.BattleRecord;
import com.nba.predict.entity.GameRecord;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.BattleRecordMapper;
import com.nba.predict.mapper.GameRecordMapper;
import com.nba.predict.service.GameRecordService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class GameRecordServiceImpl implements GameRecordService {

    private final GameRecordMapper gameRecordMapper;
    private final BattleRecordMapper battleRecordMapper;

    @Override
    public Page<GameRecord> listGames(int page, int size, String season,
                                      LocalDate gameDate, Long teamId) {
        Page<GameRecord> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<GameRecord> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(season)) {
            wrapper.eq(GameRecord::getSeason, season);
        }
        if (gameDate != null) {
            wrapper.eq(GameRecord::getGameDate, gameDate);
        }
        if (teamId != null) {
            wrapper.and(w -> w.eq(GameRecord::getHomeTeamId, teamId)
                    .or().eq(GameRecord::getAwayTeamId, teamId));
        }
        wrapper.orderByDesc(GameRecord::getGameDate);

        return gameRecordMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public GameRecord getGameDetail(Long gameId) {
        GameRecord game = gameRecordMapper.selectById(gameId);
        if (game == null) {
            throw new BusinessException(ResultCode.GAME_NOT_FOUND);
        }
        return game;
    }

    @Override
    public Object getBattleRecord(Long team1Id, Long team2Id, String season) {
        LambdaQueryWrapper<BattleRecord> wrapper = new LambdaQueryWrapper<>();
        wrapper.and(w -> w
                .and(inner -> inner.eq(BattleRecord::getTeam1Id, team1Id).eq(BattleRecord::getTeam2Id, team2Id))
                .or(inner -> inner.eq(BattleRecord::getTeam1Id, team2Id).eq(BattleRecord::getTeam2Id, team1Id)));
        if (StringUtils.hasText(season)) {
            wrapper.eq(BattleRecord::getSeason, season);
        }
        wrapper.orderByDesc(BattleRecord::getSeason);

        List<BattleRecord> records = battleRecordMapper.selectList(wrapper);

        Map<String, Object> result = new HashMap<>();
        result.put("battle_records", records);
        result.put("team1_id", team1Id);
        result.put("team2_id", team2Id);
        return result;
    }
}
