package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.PredictRecord;
import com.nba.predict.entity.Team;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.PredictRecordMapper;
import com.nba.predict.mapper.TeamMapper;
import com.nba.predict.service.RecordService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecordServiceImpl implements RecordService {

    private final PredictRecordMapper predictRecordMapper;
    private final TeamMapper teamMapper;

    @Override
    public Page<PredictRecord> listRecords(int page, int size, String predictType,
                                           LocalDate startDate, LocalDate endDate, String status) {
        Page<PredictRecord> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<PredictRecord> wrapper = new LambdaQueryWrapper<>();

        if (StringUtils.hasText(predictType)) {
            wrapper.eq(PredictRecord::getPredictType, predictType);
        }
        if (startDate != null) {
            wrapper.ge(PredictRecord::getGameDate, startDate);
        }
        if (endDate != null) {
            wrapper.le(PredictRecord::getGameDate, endDate);
        }
        if (StringUtils.hasText(status)) {
            wrapper.eq(PredictRecord::getStatus, status);
        }
        wrapper.orderByDesc(PredictRecord::getCreateTime);

        Page<PredictRecord> result = predictRecordMapper.selectPage(pageParam, wrapper);
        fillTeamNames(result.getRecords());
        return result;
    }

    /**
     * 列表页需要展示球队名称，按 team_id 批量查询后回填。
     * 用一次批量查询代替逐行查询，避免 N+1。
     */
    private void fillTeamNames(List<PredictRecord> records) {
        if (records == null || records.isEmpty()) {
            return;
        }
        Set<Long> teamIds = new HashSet<>();
        for (PredictRecord record : records) {
            if (record.getHomeTeamId() != null) {
                teamIds.add(record.getHomeTeamId());
            }
            if (record.getAwayTeamId() != null) {
                teamIds.add(record.getAwayTeamId());
            }
        }
        if (teamIds.isEmpty()) {
            return;
        }
        Map<Long, String> names = teamMapper.selectBatchIds(teamIds).stream()
                .collect(Collectors.toMap(Team::getTeamId, Team::getTeamName));
        for (PredictRecord record : records) {
            record.setHomeTeamName(names.get(record.getHomeTeamId()));
            record.setAwayTeamName(names.get(record.getAwayTeamId()));
        }
    }

    @Override
    public PredictRecord getRecordDetail(Long predictId) {
        PredictRecord record = predictRecordMapper.selectById(predictId);
        if (record == null) {
            throw new BusinessException(ResultCode.DATA_NOT_FOUND);
        }
        return record;
    }

    @Override
    public void calibrateRecord(Long predictId, Integer realPoints, Double realFgPct,
                                Integer realHomeScore, Integer realAwayScore) {
        PredictRecord record = getRecordDetail(predictId);

        record.setRealPoints(realPoints);
        record.setRealFgPct(realFgPct);
        record.setRealHomeScore(realHomeScore);
        record.setRealAwayScore(realAwayScore);

        if (realHomeScore != null && realAwayScore != null) {
            record.setRealTotalScore(realHomeScore + realAwayScore);
            record.setRealScoreDiff(realHomeScore - realAwayScore);
        }

        // 计算误差
        if (realPoints != null && record.getPredictPointsMid() != null) {
            record.setErrorPoints(Math.abs(realPoints - record.getPredictPointsMid()));
        }
        if (record.getRealTotalScore() != null && record.getPredictTotalScore() != null) {
            record.setErrorTotal(Math.abs(record.getRealTotalScore() - record.getPredictTotalScore()));
        }
        if (record.getRealScoreDiff() != null && record.getPredictScoreDiff() != null) {
            record.setErrorDiff(Math.abs(record.getRealScoreDiff() - record.getPredictScoreDiff()));
        }

        record.setStatus("CALIBRATED");
        predictRecordMapper.updateById(record);

        log.info("预测记录已校准: predictId={}", predictId);
    }
}
