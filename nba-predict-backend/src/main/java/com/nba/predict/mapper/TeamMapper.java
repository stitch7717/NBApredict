package com.nba.predict.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.nba.predict.entity.Team;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TeamMapper extends BaseMapper<Team> {
}
