import VideoReceiveData from '../../../models/VideoReceiveData.js';
import { Op, fn, col, literal } from 'sequelize';
import { getAllDetectionZones } from '../events/events.model.js';

export const getRealtimeTemp = async (req, res) => {
  try {
    const { cameraId } = req.query;
    const where = {};
    if (cameraId) where.fk_camera_id = cameraId;

    // 현재 시간에서 1분 전 시간 계산
    const oneMinuteAgo = new Date(Date.now() - 60 * 1000);
    where.create_date = {
      [Op.gte]: oneMinuteAgo
    };

    const rows = await VideoReceiveData.findAll({
      where,
      order: [['create_date', 'DESC']]
    });
    rows.reverse();
    const result = rows.map(row => {
      const v = row.getDataValue('data_value') || {};
      // JSON 파싱 추가
      const parsedV = typeof v === 'string' ? JSON.parse(v) : v;
      // console.log('======>  parsedV', parsedV);
      return {
        time: row.getDataValue('create_date'),
        rois: Array.from({ length: 10 }, (_, i) => parsedV[`data_${22 + i * 2}`] ?? null),
        min: parsedV.data_19 ?? null,
        max: parsedV.data_20 ?? null,
        avg: parsedV.data_21 ?? null,
      };
    });
    res.json({ result });
  } catch (e) {
    console.error('Error in getRealtimeTemp:', e);
    res.status(500).json({ error: e.message });
  }
};

export const getDailyRoiAvgTemp = async (req, res) => {
  try {
    const { cameraId } = req.query;
    const where = {};
    // 오늘 날짜의 시작과 끝 시간 설정
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    console.log(today, tomorrow)
    const oneDay = new Date(Date.now() - 60 * 60 * 24 * 1000);
    where.create_date = {
      [Op.gte]: oneDay
    };

    const rows = await VideoReceiveData.findAll({
      where,
      attributes: [
        'data_value',
        [fn('DATE', col('create_date')), 'date']
      ],
      order: [['create_date', 'ASC']]
    });

    // ROI별 온도 데이터 추출 및 평균 계산
    const roiTemps = Array.from({ length: 10 }, () => []);

    rows.forEach(row => {
      const dataValue = row.getDataValue('data_value') || {};
      // JSON 파싱 추가
      const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;
      if (parsedDataValue) {
        for (let i = 0; i < 10; i++) {
          const temp = parsedDataValue[`data_${22 + i * 2}`];
          if (temp !== null && temp !== undefined) {
            roiTemps[i].push(temp);
          }
        }
      }
    });

    // 각 ROI의 평균 온도 계산
    const result = roiTemps.map((temps, index) => {
      const validTemps = temps.filter(temp => temp !== null && temp !== undefined);
      const avgTemp = validTemps.length > 0
        ? validTemps.reduce((sum, temp) => sum + temp, 0) / validTemps.length
        : null;

      return {
        roi: `ROI${index + 1}`,
        averageTemp: avgTemp !== null ? Number(avgTemp.toFixed(1)) : null,
        dataCount: validTemps.length
      };
    });

    res.json({
      result,
      date: today.toISOString().split('T')[0],
      totalDataPoints: rows.length
    });
  } catch (e) {
    console.error('Error in getDailyRoiAvgTemp:', e);
    res.status(500).json({ error: e.message });
  }
};

export const getDailyRoiMinChange = async (req, res) => {
  try {
    const { cameraId } = req.query;
    const where = {};
    if (cameraId) where.fk_camera_id = cameraId;

    const oneDay = new Date(Date.now() - 60 * 60 * 24 * 1000);
    where.create_date = {
      [Op.gte]: oneDay
    };
    const rows = await VideoReceiveData.findAll({
      where,
      attributes: ['data_value'],
      order: [['create_date', 'ASC']]
    });

    // // 데이터가 없으면 빈 배열 반환
    // if (rows.length === 0) {
    //   return res.json({ result: [] });
    // }

    // ROI별 온도 데이터 추출
    const roiTemps = Array.from({ length: 10 }, () => []);

    rows.forEach(row => {
      const dataValue = row.getDataValue('data_value') || {};
      // JSON 파싱 추가
      const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;
      if (parsedDataValue) {
        for (let i = 0; i < 10; i++) {
          const temp = parsedDataValue[`data_${22 + i * 2}`];
          if (temp !== null && temp !== undefined) {
            roiTemps[i].push(temp);
          }
        }
      }
    });

    // 각 ROI의 평균, 최소, 변화율 계산
    let result = roiTemps.map((temps, index) => {
      const validTemps = temps.filter(temp => temp !== null && temp !== undefined);
      const avgTemp = validTemps.length > 0
        ? validTemps.reduce((sum, temp) => sum + temp, 0) / validTemps.length
        : null;
      const minTemp = validTemps.length > 0
        ? Math.min(...validTemps)
        : null;
      const changeRate = (avgTemp && minTemp !== null)
        ? Number((((avgTemp - minTemp) / avgTemp) * 100).toFixed(1))
        : null;
      return {
        roi: `ROI${index + 1}`,
        averageTemp: avgTemp !== null ? Number(avgTemp.toFixed(1)) : null,
        minTemp: minTemp !== null ? Number(minTemp.toFixed(1)) : null,
        changeRate
      };
    });

    // 변화율 내림차순 정렬
    result = result
      .map((item, idx) => ({ ...item, no: idx + 1 }))
      .sort((a, b) => (b.changeRate ?? -Infinity) - (a.changeRate ?? -Infinity))
      .map((item, idx) => ({ ...item, no: idx + 1 }));

    res.json({ result });
  } catch (e) {
    console.error('Error in getDailyRoiMinChange:', e);
    res.status(500).json({ error: e.message });
  }
};

export const getRoiDataList = async (req, res) => {
  try {
    // Get detection zones from events model
    const zones = await getAllDetectionZones();
    // console.log('======>  zones', zones);

    // Get the latest 2 video receive data records
    const latestData = await VideoReceiveData.findAll({
      order: [['create_date', 'DESC']],
      limit: 2
    });
    //console.log('======>  latestData', latestData);
    if (!latestData || latestData.length === 0) {
      return res.json({
        success: true,
        result: zones.map(zone => ({
          zone_desc: zone.zone_desc,
          maxTemp: '--',
          minTemp: '--',
          avgTemp: '--',
          alertLevel: zone.alert_level,
          temps: []
        }))
      });
    }

    // Process each zone
    const roiData = zones.map(zone => {
      // Calculate data field indices based on zone_type
      const zoneType = parseInt(zone.zone_type.replace('Z', ''));
      const baseIndex = 22 + (zoneType * 2);
      const minDataField = `data_${baseIndex}`;
      const maxDataField = `data_${baseIndex + 1}`;

      // Collect all temperature values for this zone
      const allMinTemps = [];
      const allMaxTemps = [];
      const allAvgTemps = [];
      const temps = [];

      latestData.forEach(data => {
        // data_value는 이미 파싱된 객체 (모델의 get() 메서드에서 처리됨)
        const dataValue = data.getDataValue('data_value') || {};
        // JSON 파싱 추가
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        // console.log('======>  dataValue', dataValue);
        // console.log('======>  minDataField', minDataField);
        // console.log('======>  maxDataField', maxDataField);
        // console.log('======>  dataValue[minDataField]', parsedDataValue[minDataField]);
        // console.log('======>  dataValue[maxDataField]', parsedDataValue[maxDataField]);

        // 데이터 필드가 존재하는지 확인
        if (parsedDataValue[minDataField] !== undefined && parsedDataValue[maxDataField] !== undefined) {
          const minTemp = Number(parsedDataValue[minDataField]);
          const maxTemp = Number(parsedDataValue[maxDataField]);
          const avgTemp = (maxTemp + minTemp) / 2;

          // console.log('======>  minTemp', minTemp);
          // console.log('======>  maxTemp', maxTemp);
          // console.log('======>  avgTemp', avgTemp);

          allMinTemps.push(minTemp);
          allMaxTemps.push(maxTemp);
          allAvgTemps.push(avgTemp);

          temps.push({
            time: data.getDataValue('create_date'),
            min: minTemp.toFixed(1),
            max: maxTemp.toFixed(1),
            avg: avgTemp.toFixed(1)
          });
        }
      });

      // Calculate overall statistics
      let maxTemp = '--';
      let minTemp = '--';
      let avgTemp = '--';

      if (allMinTemps.length > 0 && allMaxTemps.length > 0) {
        maxTemp = Math.max(...allMaxTemps).toFixed(1);
        minTemp = Math.min(...allMinTemps).toFixed(1);
        avgTemp = (allAvgTemps.reduce((a, b) => a + b, 0) / allAvgTemps.length).toFixed(1);
      }

      return {
        zone_desc: zone.zone_desc,
        maxTemp,
        minTemp,
        avgTemp,
        alertLevel: zone.alert_level,
        temps: temps.reverse() // Reverse to get chronological order
      };
    });

    res.json({
      success: true,
      result: roiData
    });
  } catch (error) {
    console.error('Error in getRoiDataList:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get ROI data list'
    });
  }
};

// ROI 번호와 발생 일자를 받아서 해당 시간 이전의 1분 데이터를 조회하는 API
export const getRoiTimeSeriesData = async (req, res) => {
  try {
    const { roiNumber, eventDate } = req.query;

    // 필수 파라미터 검증
    if (!roiNumber || !eventDate) {
      return res.status(400).json({
        success: false,
        error: 'ROI 번호와 발생 일자는 필수입니다.'
      });
    }

    // 발생 일자를 Date 객체로 변환
    const eventDateTime = new Date(eventDate);
    if (isNaN(eventDateTime.getTime())) {
      return res.status(400).json({
        success: false,
        error: '유효하지 않은 날짜 형식입니다.'
      });
    }

    // 1분 이전 시간 계산
    const oneMinuteBefore = new Date(eventDateTime.getTime() - 60 * 1000);

    console.log('ROI Time Series Data Request:', {
      roiNumber,
      eventDate,
      eventDateTime: eventDateTime.toISOString(),
      oneMinuteBefore: oneMinuteBefore.toISOString()
    });

    // ROI 번호에 해당하는 zone_type 계산
    const zoneType = `Z${roiNumber}`;

    // 데이터 필드 인덱스 계산
    const baseIndex = 22 + (parseInt(roiNumber) * 2);
    const minDataField = `data_${baseIndex}`;
    const maxDataField = `data_${baseIndex + 1}`;

    // VideoReceiveData에서 해당 시간 범위의 데이터 조회
    const timeSeriesData = await VideoReceiveData.findAll({
      where: {
        create_date: {
          [Op.between]: [oneMinuteBefore, eventDateTime]
        }
      },
      order: [['create_date', 'ASC']],
      attributes: ['create_date', 'data_value']
    });

    console.log(`Found ${timeSeriesData.length} records for ROI ${roiNumber}`);

    // 온도 데이터 추출 및 처리
    const temperatureData = [];
    const allMinTemps = [];
    const allMaxTemps = [];
    const allAvgTemps = [];

    timeSeriesData.forEach(data => {
      try {
        const dataValue = data.getDataValue('data_value') || {};
        const parsedDataValue = typeof dataValue === 'string' ? JSON.parse(dataValue) : dataValue;

        // 해당 ROI의 데이터 필드가 존재하는지 확인
        if (parsedDataValue[minDataField] !== undefined && parsedDataValue[maxDataField] !== undefined) {
          const minTemp = Number(parsedDataValue[minDataField]);
          const maxTemp = Number(parsedDataValue[maxDataField]);
          const avgTemp = (maxTemp + minTemp) / 2;

          allMinTemps.push(minTemp);
          allMaxTemps.push(maxTemp);
          allAvgTemps.push(avgTemp);

          temperatureData.push({
            time: data.getDataValue('create_date'),
            min: minTemp.toFixed(1),
            max: maxTemp.toFixed(1),
            avg: avgTemp.toFixed(1),
            roiNumber: parseInt(roiNumber)
          });
        }
      } catch (error) {
        console.error('Error parsing data for record:', data.id, error);
      }
    });

    // 통계 계산
    let maxTemp = '--';
    let minTemp = '--';
    let avgTemp = '--';

    if (allMinTemps.length > 0 && allMaxTemps.length > 0) {
      maxTemp = Math.max(...allMaxTemps).toFixed(1);
      minTemp = Math.min(...allMinTemps).toFixed(1);
      avgTemp = (allAvgTemps.reduce((a, b) => a + b, 0) / allAvgTemps.length).toFixed(1);
    }

    // 응답 데이터 구성
    const responseData = {
      roiNumber: parseInt(roiNumber),
      eventDate: eventDateTime.toISOString(),
      timeRange: {
        start: oneMinuteBefore.toISOString(),
        end: eventDateTime.toISOString()
      },
      statistics: {
        maxTemp,
        minTemp,
        avgTemp,
        dataCount: temperatureData.length
      },
      timeSeriesData: temperatureData
    };

    res.json({
      success: true,
      result: responseData
    });

  } catch (error) {
    console.error('Error in getRoiTimeSeriesData:', error);
    res.status(500).json({
      success: false,
      error: 'ROI 시계열 데이터 조회 중 오류가 발생했습니다.'
    });
  }
};