import { DataTypes } from 'sequelize';

export default (sequelize) => {
  const VideoPanoramaData = sequelize.define('VideoPanoramaData', {
    id: {
      type: DataTypes.INTEGER(11),
      primaryKey: true,
      autoIncrement: true,
      allowNull: false
    },
    panoramaData: {
      type: DataTypes.TEXT('long'),
      allowNull: true,
      field: 'panoramaData',  // 테이블 필드명과 매핑
      validate: {
        isValidJSON(value) {
          if (value !== null && value !== '') {
            try {
              JSON.parse(value);
            } catch (error) {
              throw new Error('panoramaData must be a valid JSON string');
            }
          }
        }
      }
    },
    create_date: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW
    }
  }, {
    tableName: 'tb_video_panorama_data',
    timestamps: false,
    charset: 'latin1',
    collate: 'latin1_general_ci',
    // panoramaData 필드는 utf8mb4_bin collation 사용
    define: {
      charset: 'latin1',
      collate: 'latin1_general_ci'
    }
  });

  return VideoPanoramaData;
};
