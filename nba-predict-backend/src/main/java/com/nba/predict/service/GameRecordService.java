package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.GameRecord;

import java.time.LocalDate;

public interface GameRecordService {

    Page<GameRecord> listGames(int page, int size, String season,
                               LocalDate gameDate, Long teamId);

    GameRecord getGameDetail(Long gameId);

    Object getBattleRecord(Long team1Id, Long team2Id, String season);
}
