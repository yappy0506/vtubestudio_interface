# VTube Studio API

- [VTube Studio API](#vtube-studio-api)
  - [VTSのAPI一覧](#vtsのapi一覧)
    - [APIStateRequest](#apistaterequest)
    - [VTubeStudioAPIStateBroadcast](#vtubestudioapistatebroadcast)
    - [AuthenticationTokenRequest](#authenticationtokenrequest)
    - [StatisticsRequest](#statisticsrequest)
    - [VTSFolderInfoRequest](#vtsfolderinforequest)
    - [CurrentModelRequest](#currentmodelrequest)
    - [AvailableModelsRequest](#availablemodelsrequest)
    - [ModelLoadRequest](#modelloadrequest)
    - [MoveModelRequest](#movemodelrequest)
- [---ここまで確認済み---](#---ここまで確認済み---)
    - [HotkeysInCurrentModelRequest](#hotkeysincurrentmodelrequest)
    - [HotkeyTriggerRequest](#hotkeytriggerrequest)
    - [ExpressionStateRequest](#expressionstaterequest)
    - [ExpressionActivationRequest](#expressionactivationrequest)
    - [ArtMeshListRequest](#artmeshlistrequest)
    - [ColorTintRequest](#colortintrequest)
    - [SceneColorOverlayInfoRequest](#scenecoloroverlayinforequest)
    - [FaceFoundRequest](#facefoundrequest)
    - [InputParameterListRequest](#inputparameterlistrequest)
    - [ParameterValueRequest](#parametervaluerequest)
    - [Live2DParameterListRequest](#live2dparameterlistrequest)
    - [ParameterCreationRequest](#parametercreationrequest)
    - [ParameterDeletionRequest](#parameterdeletionrequest)
    - [InjectParameterDataRequest](#injectparameterdatarequest)
    - [GetCurrentModelPhysicsRequest](#getcurrentmodelphysicsrequest)
    - [SetCurrentModelPhysicsRequest](#setcurrentmodelphysicsrequest)
    - [NDIConfigRequest](#ndiconfigrequest)
    - [ItemListRequest](#itemlistrequest)
    - [ItemLoadRequest](#itemloadrequest)
    - [ItemUnloadRequest](#itemunloadrequest)
    - [ItemAnimationControlRequest](#itemanimationcontrolrequest)
    - [ItemMoveRequest](#itemmoverequest)
    - [ItemSortRequest](#itemsortrequest)
    - [ArtMeshSelectionRequest](#artmeshselectionrequest)
    - [ItemPinRequest](#itempinrequest)
    - [PostProcessingListRequest](#postprocessinglistrequest)
    - [PostProcessingUpdateRequest](#postprocessingupdaterequest)
  - [イベントの購読(サブスクライブ)と購読解除(アンサブスクライブ)](#イベントの購読サブスクライブと購読解除アンサブスクライブ)
    - [EventSubscriptionRequest](#eventsubscriptionrequest)

## VTSのAPI一覧
タイトルは`messageType`としてAPIの一覧を以下に示す。

取得元URL:
https://github.com/DenchiSoft/VTubeStudio/?tab=readme-ov-file#requesting-list-of-available-items-or-items-in-scene

### APIStateRequest

- apiの概要
  - API状態とセッション認証状態を確認するAPIである。
  - 主要データ:
    - `active`: 
      API有効状態
    - `vTubeStudioVersion`:
      アプリバージョン
    - `currentSessionAuthenticated`:
      この接続が認証済みか、接続直後のヘルスチェックと認証フロー分岐に使う。

- 実運用のイメージ
  1. 接続直後に`APIStateRequest`を送信する。
  2. `active`と`currentSessionAuthenticated`を見て次の処理(認証/通常処理)を分岐する。
  3. 再接続時にも同じ手順でセッション状態を再確認する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "APIStateRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "APIStateResponse",
    "data": {
      "active": true,
      "vTubeStudioVersion": "1.29.0",
      "currentSessionAuthenticated": true
    }
  }
  ```

### VTubeStudioAPIStateBroadcast

- apiの概要
  - 当APIはVTube StudioがUDP 47779で2秒ごとに送信する状態ブロードキャストを受信するための情報である。
  - 主要データ:
    - `active`:
      対象のサーバにおいてAPIが有効か
    - `port`:
      WebSocket接続先ポート
    - `instanceID`:
      インスタンス固有ID
      起動中は不変で、複数起動時の識別に使える。
    - `windowTitle`:
      識別用ウィンドウ名

- 実運用のイメージ
  1. UDP 47779 をListenしてブロードキャストを受信する。
  2. `active=true`のデータを抽出し、`port`からWebSocket接続先を決める。
  3. 複数起動時は`instanceID`と`windowTitle`で接続対象を特定する。

- Request例
  このAPIはUDPブロードキャスト受信専用のためRequestはない。

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "VTubeStudioAPIStateBroadcast",
    "messageType": "VTubeStudioAPIStateBroadcast",
    "data": {
      "active": false,
      "port": 8001,
      "instanceID": "93aa0d0494304fddb057ae8a295c4e59",
      "windowTitle": "VTube Studio"
    }
  }
  ```

### AuthenticationTokenRequest

- apiの概要
  - APIサーバとの通信の前に初回認可用のトークンを取得するAPIである。
    VtubeStudioはRequestを受け取った後、Userの操作を受け付けることで、プラグインにAPI使用を許可する。
  - 主要データ:
    - Request:
      - `pluginName`:
        プラグイン名(3-32文字)
      - `pluginDeveloper`:
        プラグイン開発者名(3〜32文字)
      - `pluginIcon`:
        プラグインのアイコン画像(128x128 base64画像、送信は任意)
        プラグインアクセス要求ポップアップでこのアイコンが使用される。
      - `authenticationToken`:
        認証を求める際のトークンである。
        初回認証のResponseによって得たものを、二度目以降の認証要求で用いる。
        Responseに当データが含まれる場合、VTSの認証操作にUserの手は入らない。
    - Response:
      - `authenticationToken`: 
        初認証成功時には、APIで認証を行うトークンとして当データを得る。
        次のセッションでも同じトークンを使って再度認証できるため、再びトークン取得リクエストを送る必要はない。
      - `errorID`:
      - `message`:
        失敗時には50、"User has denied API access for your plugin."と返す。
        失敗の理由がVTSからの拒否である場合、以降の要求はエラーとなる。
        この場合は再認証を行ってよい。

- 実運用のイメージ
  1. `APIStateRequest`で未認証であることを確認する。
  2. `pluginName`と`pluginDeveloper`を設定して送信し、VTS側の許可ポップアップ応答を待つ。
  3. 返却された`authenticationToken`を安全に保存し、以後は`AuthenticationRequest`で再利用する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "AuthenticationTokenRequest",
    "data": {
      "pluginName": "My Cool Plugin",
      "pluginDeveloper": "My Name",
      "pluginIcon": "iVBORw0..."
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "AuthenticationTokenResponse",
    "data": {
      "authenticationToken": "adcd-123-ef09-some-token-string-abcd"
    }
  }
  ```

### StatisticsRequest

- apiの概要
  - 稼働統計とウィンドウ情報を取得するAPIである。
    座標変換や接続監視の基準値として利用する。
  - 主要データ:
    - `uptime`:
      vts起動からの経過時刻[ms]
    - `framerate`:
      現在のFPS
    - `allowedPlugins`:
      プラグインに対する許可数
    - `connectedPlugins`:
      プラグインの接続数
    - `startedWithSteam`:
      アプリがSteam経由で起動されているか
      Steam経由の場合はtrue、そうでない場合はfalseとなる。
      falseのときは、Steamを使わず.batファイルでVTSを起動した場合と考えられる。
    - `windowWidth`:
      ウィンドウの幅[px]
    - `windowHeight`:
      ウィンドウの高さ[px]
    - `windowIsFullscreen`:
      ウィンドウがフルスクリーンであるか

- 実運用のイメージ
  1. 低頻度で`StatisticsRequest`を送信する。
  2. `framerate`と`windowWidth`/`windowHeight`を取得して、負荷監視や座標計算に使う。
  3. 異常値が出た場合はUI更新頻度や制御周期を下げる。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "StatisticsRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "StatisticsResponse",
    "data": {
      "uptime": 1439384,
      "framerate": 73,
      "vTubeStudioVersion": "1.9.0",
      "allowedPlugins": 7,
      "connectedPlugins": 2,
      "startedWithSteam": true,
      "windowWidth": 1031,
      "windowHeight": 812,
      "windowIsFullscreen": false
    }
  }
  ```

### VTSFolderInfoRequest

- apiの概要
  - VTSの主要フォルダ名を取得するAPIである。
    フォルダはゲームファイル内のStreamingAssetsフォルダに配置されているものである。
  - 主要データ:
    - `models`:
      モデルが収められているStreamingAssets配下の論理フォルダ名
    - `items`:
      アイテムが収められているStreamingAssets配下の論理フォルダ名
    - `config`:
      configが収められているStreamingAssets配下の論理フォルダ名
    - `logs`:
      ログが収められているStreamingAssets配下の論理フォルダ名

- 実運用のイメージ
  1. 起動時に1回`VTSFolderInfoRequest`を送る。
  2. `models`/`items`/`config`/`logs`をアプリ設定へキャッシュする。
  3. ファイル参照処理ではこのキャッシュを使って相対パスを解決する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "VTSFolderInfoRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "VTSFolderInfoResponse",
    "data": {
      "models": "Live2DModels",
      "backgrounds": "Backgrounds",
      "items": "Items",
      "config": "Config",
      "logs": "Logs",
      "backup": "Backup"
    }
  }
  ```

### CurrentModelRequest

- apiの概要
  - 現在ロード中のモデルと現在の配置を取得するAPIである。
  - 主要データ:
    - `modelLoaded`:
      モデルがロードされているか
      されている場合`true`、されていない場合、もしくは処理中の場合`false`となる。
    - `modelName`:
      ロード中のモデルの表示名
      `modelLoaded=false`の場合は空文字になる。
    - `modelID`:
      ロード中のモデルを一意に識別するID
      モデル切替時の`ModelLoadRequest`で利用できる。
    - `vtsModelName`:
      VTSモデルの設定ファイル名(`.vtube.json`)
      モデルフォルダからの相対ファイル名として返る。
    - `vtsModelIconName`:
      VTSのモデル選択バーで使われるアイコンのファイル名
      アイコン未設定時は空文字になる。
    - `live2DModelName`:
      Live2D本体のモデルファイル名(`.model3.json`)
      モデルフォルダからの相対ファイル名として返る。
    - `modelLoadTime`:
      モデルのロードに要した時間[ms]
    - `timeSinceModelLoaded`:
      現在のモデルがロードされてからの経過時間[ms]
    - `numberOfLive2DParameters`:
      モデルに含まれるLive2Dパラメータ数
    - `numberOfLive2DArtmeshes`:
      モデルに含まれるArtMesh数
    - `hasPhysicsFile`:
      モデルに有効な物理設定ファイルがあるか
    - `numberOfTextures`:
      モデルが参照しているテクスチャ枚数
    - `textureResolution`:
      テクスチャ解像度(正方テクスチャの1辺ピクセル数)
    - `modelPosition`:
      モデルの配置情報
      `positionX`/`positionY`は座標、`rotation`は角度、`size`はモデルのサイズを表す。

- 実運用のイメージ
  1. モデル制御前に`CurrentModelRequest`を送る。
  2. `modelLoaded`が`true`のときだけ`modelPosition`を基準に制御値を計算する。
  3. `false`の場合はロード待ちまたは`AvailableModelsRequest`へ遷移する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "CurrentModelRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "CurrentModelResponse",
    "data": {
      "modelLoaded": true,
      "modelName": "My Currently Loaded Model",
      "modelID": "UniqueID",
      "modelPosition": {
        "positionX": -0.1,
        "positionY": 0.4,
        "rotation": 9.33,
        "size": -61.9
      }
    }
  }
  ```

### AvailableModelsRequest

- apiの概要
  - ロード可能モデルの一覧を取得するAPIである。
  - 主要データ:
    - `numberOfModels`:
      利用可能なモデルの数
    - `availableModels[]`:
      利用可能なモデル情報の配列
      配列には以下のデータが収められる。
      - `modelLoaded`:
        そのモデルが現在ロード中か
      - `modelName`:
        各モデルの表示名
      - `modelID`:
        各モデルを一意に識別するID
      - `vtsModelName`:
        VTube Studio内部で使用されるモデル名
        ファイル/フォルダ由来の内部名称
      - `vtsModelIconName`:
        モデルアイコン画像の内部名
        アイコンファイル識別子

- 実運用のイメージ
  1. `AvailableModelsRequest`で一覧を取得する。
  2. `availableModels[]`から対象`modelID`を選択する。
  3. 選択した`modelID`を`ModelLoadRequest`に渡して切り替える。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "AvailableModelsRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "AvailableModelsResponse",
    "data": {
      "numberOfModels": 2,
      "availableModels": [
        {
          "modelLoaded": false,
          "modelName": "Model A",
          "modelID": "A"
        },
        {
          "modelLoaded": true,
          "modelName": "Model B",
          "modelID": "B"
        }
      ]
    }
  }
  ```

### ModelLoadRequest

- apiの概要
  - 指定`modelID`のモデルをロードするAPIである。
    アプリが現在、モデルの読み込み／アンロードを行えない状態にある場合、この処理は失敗してエラーを返すことがある。
    これには、設定ウィンドウが開いている場合や、すでにモデルの読み込み処理が進行中である場合などが含まれる。
  - 主要データ:
    - Request:
      - `modelID`:
        対象モデルID。空文字ならアンロード
    - Response:
      - `modelID`:
        実際にロードされたモデルID

- 実運用のイメージ
  1. 切替対象の`modelID`を決めて`ModelLoadRequest`を送信する。
  2. `ModelLoadResponse`の`modelID`を確認して切替成功を判定する。
  3. 失敗時はUI状態やクールダウン経過後に再試行する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ModelLoadRequest",
    "data": {
      "modelID": "UniqueIDOfModelToLoad"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ModelLoadResponse",
    "data": {
      "modelID": "UniqueIDOfModelThatWasJustLoaded"
    }
  }
  ```

### MoveModelRequest

- apiの概要
  - 現在読み込まれているモデルの位置/回転/サイズを更新するAPIである。
    Requestで未指定の値は現値維持される。
    またモデルが読み込まれていない場合はエラーとなる。
  - 主要データ:
    - `timeInSeconds`:
      移動にかける時間0〜2[s]
    - `valuesAreRelativeToModel`:
      以下の値が現在からの相対値か絶対値か
      `true`の場合は相対値、`false`の場合は絶対値である。
    - `positionX`:
      x軸の目標値
      値は-1000～1000までである。
    - `positionY`:
      y軸の目標値
      値は-1000～1000までである。
    - `rotation`:
      回転角の目標値
      値は-360～360までである。
      時計回りが正の値である。
    - `size`:
      モデルのサイズの目標値
      値は-100～100までである。

  VTSの座標系
  ![](2026-02-24-20-27-20.png)

- 実運用のイメージ
  1. 現在姿勢を基準に目標値(位置/回転/サイズ)を算出する。
  2. `valuesAreRelativeToModel`と`timeInSeconds`を指定して送る。
  3. 連続制御時は短い周期で再送し、最新リクエストで上書きする。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "MoveModelRequest",
    "data": {
      "timeInSeconds": 0.2,
      "valuesAreRelativeToModel": false,
      "positionX": 0.1,
      "positionY": -0.7,
      "rotation": 16.3,
      "size": -22.5
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "MoveModelResponse",
    "data": {}
  }
  ```




# ---ここまで確認済み---



### HotkeysInCurrentModelRequest

- apiの概要
  - モデルまたはLive2D Itemのホットキー一覧を取得するAPIである。
  - 主要データ:
    - Request:
      - `modelID`:
        任意・対象モデル
      - `live2DItemFileName`:
        任意・対象Live2D Item
    - Response:
      - `availableHotkeys[]`:
        取得できたホットキー情報の配列
      - `hotkeyID`:
        各ホットキーを一意に識別するID
      - `name`:
        ホットキーの表示名
      - `type`:
        ホットキーの種別（表情切替・アニメ実行など）
      - `description`:
        ホットキーの補足説明文
      - `onScreenButtonID`:
        オンスクリーンボタンに紐づくID（存在する場合）

- 実運用のイメージ
  1. 対象モデルまたはLive2D Itemを決めて一覧取得する。
  2. `availableHotkeys[]` から実行候補の `hotkeyID` を選ぶ。
  3. 選んだ `hotkeyID` を `HotkeyTriggerRequest` に渡す。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "HotkeysInCurrentModelRequest",
    "data": {
      "modelID": "OptionalModelID",
      "live2DItemFileName": "OptionalLive2DItemFileName"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "HotkeysInCurrentModelResponse",
    "data": {
      "modelLoaded": true,
      "modelName": "My Model",
      "modelID": "UniqueID",
      "availableHotkeys": [
        {
          "name": "My first hotkey",
          "type": "ToggleExpression",
          "hotkeyID": "SomeUniqueId"
        }
      ]
    }
  }
  ```

### HotkeyTriggerRequest

- apiの概要
  - ホットキーを実行するAPIである。
  - 主要データ:
    - Request:
      - `hotkeyID`:
        IDまたは名称
      - `itemInstanceID`:
        任意・Live2D Item対象
    - Response:
      - `hotkeyID`:
        実行されたホットキーの一意ID

- 実運用のイメージ
  1. 実行したい `hotkeyID`（または名称）を指定して送信する。
  2. Live2D Item対象なら `itemInstanceID` も指定する。
  3. 失敗時はクールダウンやキュー上限の可能性を考慮して再試行間隔を調整する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "HotkeyTriggerRequest",
    "data": {
      "hotkeyID": "HotkeyNameOrUniqueId",
      "itemInstanceID": "OptionalItemInstanceID"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "HotkeyTriggerResponse",
    "data": {
      "hotkeyID": "UniqueIdOfHotkeyThatWasExecuted"
    }
  }
  ```

### ExpressionStateRequest

- apiの概要
  - 表情の状態一覧を取得するAPIである。
  - 主要データ:
    - Request:
      - `expressionFile`:
        任意・単体指定
      - `details`:
        詳細配列の返却有無
    - Response:
      - `expressions[]`:
        取得できた表情情報の配列
      - `file`:
        表情ファイル名（`.exp3.json`）
      - `active`:
        その表情が現在有効か
      - `usedInHotkeys`:
        当該表情を使うホットキー一覧
      - `parameters`:
        表情が操作するパラメータ情報（`details=true` 時）

- 実運用のイメージ
  1. 全件確認か単体確認かを決め、必要なら `expressionFile` を指定する。
  2. `details=true` でホットキー紐付けやパラメータ情報まで取得する。
  3. `expressions[]` を見て有効状態と次アクションを決める。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ExpressionStateRequest",
    "data": {
      "details": true,
      "expressionFile": "myExpression_optional_1.exp3.json"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ExpressionStateResponse",
    "data": {
      "modelLoaded": true,
      "modelName": "My Model",
      "modelID": "UniqueID",
      "expressions": [
        {
          "name": "myExpression",
          "file": "myExpression.exp3.json",
          "active": false
        }
      ]
    }
  }
  ```

### ExpressionActivationRequest

- apiの概要
  - 表情ファイルを直接ON/OFFするAPIである。
  - 主要データ:
    - `expressionFile`:
      対象exp3
    - `active`:
      有効/無効
    - `fadeTime`:
      フェード秒
  - 成功時Responseの `data` は空オブジェクト。

- 実運用のイメージ
  1. 対象 `expressionFile` と `active`（ON/OFF）を決める。
  2. 必要なら `fadeTime` を指定して送信する。
  3. 状態確認が必要なら `ExpressionStateRequest` で再確認する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ExpressionActivationRequest",
    "data": {
      "expressionFile": "myExpression_1.exp3.json",
      "fadeTime": 0.5,
      "active": true
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ExpressionActivationResponse",
    "data": {}
  }
  ```

### ArtMeshListRequest

- apiの概要
  - 現在モデルのArtMesh一覧を取得するAPIである。
  - 主要データ:
    - `artMeshNames[]`:
      ArtMesh ID一覧
    - `artMeshTags[]`:
      userdata由来タグ
    - `modelLoaded`:
      モデル有無
  - 色変更・選択UI・ピン留めの前準備として使う。

- 実運用のイメージ
  1. `ArtMeshListRequest` を送ってIDとタグ一覧を取得する。
  2. `artMeshNames`/`artMeshTags` から対象条件を作る。
  3. `ColorTintRequest` や `ArtMeshSelectionRequest` の入力へ流用する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ArtMeshListRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ArtMeshListResponse",
    "data": {
      "modelLoaded": true,
      "numberOfArtMeshNames": 5,
      "numberOfArtMeshTags": 2,
      "artMeshNames": [
        "ArtMesh1",
        "ArtMesh2"
      ],
      "artMeshTags": [
        "my_tag",
        "SomeOtherTag"
      ]
    }
  }
  ```

### ColorTintRequest

- apiの概要
  - 条件一致したArtMeshへティント色を適用するAPIである。
  - 主要データ:
    - Request:
      - `colorTint`:
        RGBAと照明混合率
      - `artMeshMatcher`:
        名前/タグ/番号で対象選択
    - Response:
      - `matchedArtMeshes`:
        適用件数

- 実運用のイメージ
  1. 適用色を `colorTint` に設定する。
  2. `artMeshMatcher` で対象を絞って送信する。
  3. 解除時は白（255,255,255,255）を指定してリセットする。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ColorTintRequest",
    "data": {
      "colorTint": {
        "colorR": 255,
        "colorG": 150,
        "colorB": 0,
        "colorA": 255,
        "mixWithSceneLightingColor": 1.0
      },
      "artMeshMatcher": {
        "tintAll": false,
        "nameContains": [
          "mouth"
        ],
        "tagContains": [
          "MyTag"
        ]
      }
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ColorTintResponse",
    "data": {
      "matchedArtMeshes": 3
    }
  }
  ```

### SceneColorOverlayInfoRequest

- apiの概要
  - シーン照明オーバーレイ設定と現在色を取得するAPIである。
  - 主要データ:
    - `active`:
      機能ON/OFF
    - `itemsIncluded`:
      Item反映有無
    - `baseBrightness`:
      調整値
    - `colorBoost`:
      調整値
    - `smoothing`:
      調整値
    - `colorOverlayR/G/B`:
      最終色
  - 照明連動演出の同期に使う。

- 実運用のイメージ
  1. `SceneColorOverlayInfoRequest` を周期取得する。
  2. `colorOverlayR/G/B` と `active` を見て外部演出へ反映する。
  3. `itemsIncluded` やキャプチャ方式を見て反映範囲を調整する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "SceneColorOverlayInfoRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "SceneColorOverlayInfoResponse",
    "data": {
      "active": true,
      "itemsIncluded": true,
      "isWindowCapture": false,
      "baseBrightness": 16,
      "colorBoost": 35,
      "smoothing": 6,
      "colorOverlayR": 206,
      "colorOverlayG": 150,
      "colorOverlayB": 153,
      "colorAvgR": 237,
      "colorAvgG": 157,
      "colorAvgB": 162
    }
  }
  ```

### FaceFoundRequest

- apiの概要
  - トラッカーで顔が検出中か確認するAPIである。
  - 主要データ:
    - `found`:
      検出状態 true/false
  - 追従演出やロスト時挙動の分岐に使う。

- 実運用のイメージ
  1. `FaceFoundRequest` で追跡状態を確認する。
  2. `found=false` の間は注入値やモーションを抑制する。
  3. `found=true` へ戻ったら通常制御へ復帰する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "FaceFoundRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "FaceFoundResponse",
    "data": {
      "found": true
    }
  }
  ```

### InputParameterListRequest

- apiの概要
  - 利用可能な入力パラメータ一覧を取得するAPIである。
  - 主要データ:
    - `customParameters[]`:
      プラグインが作成したカスタム入力パラメータ一覧
    - `defaultParameters[]`:
      VTS標準の入力パラメータ一覧
    - `name/value/min/max/defaultValue`:
      各パラメータの名前・現在値・範囲・初期値
  - 大きいペイロードになりやすいため高頻度呼び出しは非推奨。

- 実運用のイメージ
  1. 低頻度で一覧を取得し、利用可能パラメータを更新する。
  2. `customParameters` と `defaultParameters` を内部辞書に格納する。
  3. 以後の注入対象選択では辞書を参照して存在確認する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "InputParameterListRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "InputParameterListResponse",
    "data": {
      "modelLoaded": true,
      "modelName": "My Model",
      "modelID": "UniqueID",
      "customParameters": [
        {
          "name": "MyCustomParam",
          "addedBy": "My Plugin",
          "value": 12.4,
          "min": -30,
          "max": 30,
          "defaultValue": 0
        }
      ],
      "defaultParameters": [
        {
          "name": "FaceAngleX",
          "addedBy": "VTube Studio",
          "value": 45.78,
          "min": -30,
          "max": 30,
          "defaultValue": 0
        }
      ]
    }
  }
  ```

### ParameterValueRequest

- apiの概要
  - 単一入力パラメータ値を取得するAPIである。
  - 主要データ:
    - Request:
      - `name`:
        対象パラメータ名
    - Response:
      - `value`:
        現在値
      - `min/max/defaultValue`:
        推奨レンジ情報
      - `addedBy`:
        提供元

- 実運用のイメージ
  1. 値を確認したい `name` を指定して送信する。
  2. `value` と `min/max/defaultValue` を受け取る。
  3. 異常値診断や補正ロジックの基準として使う。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ParameterValueRequest",
    "data": {
      "name": "MyCustomParamName1"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ParameterValueResponse",
    "data": {
      "name": "MyCustomParamName1",
      "addedBy": "My Plugin Name",
      "value": 12.4,
      "min": -30,
      "max": 30,
      "defaultValue": 0
    }
  }
  ```

### Live2DParameterListRequest

- apiの概要
  - 現在モデルのLive2Dパラメータ値一覧を取得するAPIである。
  - 主要データ:
    - `parameters[]`:
      モデルに含まれるLive2Dパラメータ情報の配列
    - `name/value/min/max/defaultValue`:
      各Live2Dパラメータの名前・現在値・範囲・初期値
  - モデル未ロード時は `modelLoaded=false` かつ配列空。

- 実運用のイメージ
  1. モデルロード後に `Live2DParameterListRequest` を送る。
  2. `parameters[]` を読み取り、現在の出力状態を監視する。
  3. 必要に応じて `InjectParameterDataRequest` の入力へフィードバックする。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "Live2DParameterListRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "Live2DParameterListResponse",
    "data": {
      "modelLoaded": true,
      "modelName": "My Model",
      "modelID": "UniqueID",
      "parameters": [
        {
          "name": "ParamAngleX",
          "value": 12.4,
          "min": -30,
          "max": 30,
          "defaultValue": 0
        }
      ]
    }
  }
  ```

### ParameterCreationRequest

- apiの概要
  - カスタム入力パラメータを作成するAPIである。
  - 主要データ:
    - Request:
      - `parameterName`:
        英数字4〜32
      - `explanation`:
        任意説明
      - `min/max/defaultValue`:
        マッピング初期レンジ
    - Response:
      - `parameterName`:
        作成/更新対象名

- 実運用のイメージ
  1. 使いたいカスタムパラメータ名とレンジを定義する。
  2. 起動時に `ParameterCreationRequest` を送り、未作成なら作成する。
  3. 成功後は対象パラメータへ値注入を開始する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ParameterCreationRequest",
    "data": {
      "parameterName": "MyNewParamName",
      "explanation": "This is my new parameter.",
      "min": -50,
      "max": 50,
      "defaultValue": 10
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ParameterCreationResponse",
    "data": {
      "parameterName": "MyNewParamName"
    }
  }
  ```

### ParameterDeletionRequest

- apiの概要
  - カスタム入力パラメータを削除するAPIである。
  - 主要データ:
    - Request:
      - `parameterName`:
        削除対象名
    - Response:
      - `parameterName`:
        削除した対象名

- 実運用のイメージ
  1. 不要になった自作パラメータ名を指定して送信する。
  2. `ParameterDeletionResponse` の `parameterName` で対象一致を確認する。
  3. 関連する注入処理やUI項目を同時に削除する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ParameterDeletionRequest",
    "data": {
      "parameterName": "MyNewParamName"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ParameterDeletionResponse",
    "data": {
      "parameterName": "MyNewParamName"
    }
  }
  ```

### InjectParameterDataRequest

- apiの概要
  - 入力パラメータへ値を注入するAPIである。
  - 主要データ:
    - Request:
      - `mode`:
        注入方式。`set`（上書き）または`add`（加算）
      - `parameterValues[]`:
        注入するパラメータの配列
      - `id`:
        注入対象の入力パラメータ名
      - `value`:
        注入値
      - `weight`:
        加算時の重み（省略時は1.0）
      - `faceFound`:
        任意・顔検出状態を通知
    - Response:
      - `data`:
        成功時は空オブジェクト。失敗時はエラーレスポンスになる

- 実運用のイメージ
  1. 注入対象 `parameterValues[]` と `mode`（set/add）を決める。
  2. 送信周期を1秒未満に保って継続送信する。
  3. 競合やエラー発生時は対象パラメータとモードを見直す。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "InjectParameterDataRequest",
    "data": {
      "faceFound": false,
      "mode": "set",
      "parameterValues": [
        {
          "id": "FaceAngleX",
          "value": 12.31
        },
        {
          "id": "MyNewParamName",
          "weight": 0.8,
          "value": 0.7
        }
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "InjectParameterDataResponse",
    "data": {}
  }
  ```

### GetCurrentModelPhysicsRequest

- apiの概要
  - 現在モデルの物理設定を取得するAPIである。
  - 主要データ:
    - `baseStrength`:
      基礎値
    - `baseWind`:
      基礎値
    - `physicsGroups[]`:
      グループ別乗数
    - `apiPhysicsOverrideActive`:
      API上書き中か
  - `modelLoaded=false` の場合は物理配列は空になる。

- 実運用のイメージ
  1. 上書き前に `GetCurrentModelPhysicsRequest` で現設定を取得する。
  2. `physicsGroups[]` から有効な `groupID` を特定する。
  3. この結果を `SetCurrentModelPhysicsRequest` の入力設計に使う。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "GetCurrentModelPhysicsRequest",
    "data": {}
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "GetCurrentModelPhysicsResponse",
    "data": {
      "modelLoaded": true,
      "modelHasPhysics": true,
      "physicsSwitchedOn": true,
      "usingLegacyPhysics": false,
      "physicsFPSSetting": -1,
      "baseStrength": 50,
      "baseWind": 17,
      "apiPhysicsOverrideActive": false,
      "apiPhysicsOverridePluginName": "",
      "physicsGroups": [
        {
          "groupID": "PhysicsSetting1",
          "groupName": "Hair Front Physics",
          "strengthMultiplier": 1.5,
          "windMultiplier": 0.3
        }
      ]
    }
  }
  ```

### SetCurrentModelPhysicsRequest

- apiの概要
  - 現在モデルの物理値を一時上書きするAPIである。
  - 主要データ:
    - Request:
      - `strengthOverrides[]`:
        物理強度の上書き設定配列
      - `windOverrides[]`:
        風量の上書き設定配列
      - `id`:
        対象の物理グループID（空文字でベース値）
      - `value`:
        上書きする値
      - `setBaseValue`:
        `true` ならベース値として適用
      - `overrideSeconds`:
        上書きを維持する秒数
  - 上書きはタイマー式で、制御権は同時に1プラグインのみ。

- 実運用のイメージ
  1. 変更したい `strengthOverrides`/`windOverrides` を組み立てる。
  2. `overrideSeconds` を考慮して定期再送し、上書きを維持する。
  3. 他プラグイン競合エラー時は制御権が空くまで待機する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "SetCurrentModelPhysicsRequest",
    "data": {
      "strengthOverrides": [
        {
          "id": "PhysicsSetting1",
          "value": 1.5,
          "setBaseValue": false,
          "overrideSeconds": 2
        }
      ],
      "windOverrides": [
        {
          "id": "",
          "value": 85,
          "setBaseValue": true,
          "overrideSeconds": 5
        }
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "SetCurrentModelPhysicsResponse",
    "data": {}
  }
  ```

### NDIConfigRequest

- apiの概要
  - NDI設定を取得/更新するAPIである。
  - 主要データ:
    - `setNewConfig`:
      更新有無
    - `ndiActive`:
      NDI ON/OFF
    - `useNDI5`:
      NDI5ライブラリを使用するか
    - `useCustomResolution`:
      カスタム解像度設定を使うか
    - `customWidthNDI`:
      固定解像度
    - `customHeightNDI`:
      固定解像度
  - 更新リクエストにはクールダウンがある。

- 実運用のイメージ
  1. まず `setNewConfig=false` で現設定を取得する。
  2. 必要な設定値だけ変更して `setNewConfig=true` で更新する。
  3. クールダウンを考慮し、連続更新は3秒以上間隔を空ける。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "NDIConfigRequest",
    "data": {
      "setNewConfig": true,
      "ndiActive": true,
      "useNDI5": true,
      "useCustomResolution": true,
      "customWidthNDI": 1024,
      "customHeightNDI": 512
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "NDIConfigResponse",
    "data": {
      "setNewConfig": true,
      "ndiActive": true,
      "useNDI5": true,
      "useCustomResolution": true,
      "customWidthNDI": 1024,
      "customHeightNDI": 512
    }
  }
  ```

### ItemListRequest

- apiの概要
  - シーン内Itemとロード可能Item情報を取得するAPIである。
  - 主要データ:
    - Request:
      - `includeAvailableSpots`:
        返却配列の切替
      - `includeItemInstancesInScene`:
        返却配列の切替
      - `includeAvailableItemFiles`:
        返却配列の切替
      - `onlyItemsWithFileName`:
        指定ファイル名のItemだけ返す絞り込み条件
      - `onlyItemsWithInstanceID`:
        指定インスタンスIDのItemだけ返す絞り込み条件
    - Response:
      - `itemInstancesInScene[]`:
        現在シーンに存在するItemインスタンス一覧
      - `availableItemFiles[]`:
        ロード可能なItemファイル一覧
      - `canLoadItemsRightNow`:
        現在新規Itemをロード可能か

- 実運用のイメージ
  1. 用途に応じて `include*` フラグを設定して送信する。
  2. `itemInstancesInScene` と `availableSpots` で配置可能状態を把握する。
  3. ファイル一覧が必要な場合のみ `includeAvailableItemFiles=true` を使う。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemListRequest",
    "data": {
      "includeAvailableSpots": true,
      "includeItemInstancesInScene": true,
      "includeAvailableItemFiles": false,
      "onlyItemsWithFileName": "",
      "onlyItemsWithInstanceID": ""
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemListResponse",
    "data": {
      "itemsInSceneCount": 2,
      "totalItemsAllowedCount": 60,
      "canLoadItemsRightNow": true,
      "availableSpots": [
        -1,
        1,
        2
      ],
      "itemInstancesInScene": [
        {
          "fileName": "Ribbon",
          "instanceID": "18de...",
          "order": 1,
          "type": "Live2D"
        }
      ],
      "availableItemFiles": [
        {
          "fileName": "Ribbon",
          "type": "Live2D",
          "loadedCount": 1
        }
      ]
    }
  }
  ```

### ItemLoadRequest

- apiの概要
  - ItemをシーンへロードするAPIである。
  - 主要データ:
    - Request:
      - `fileName`:
        読み込むItemファイル名
      - `positionX`:
        X座標
      - `positionY`:
        Y座標
      - `rotation`:
        回転角度
      - `size`:
        サイズ倍率
      - `fadeTime`:
        フェード時間（秒）
      - `order`:
        描画順（前後関係）
      - `smoothing`:
        移動補間の滑らかさ
      - `locked`:
        配置をロックするか（他にも表示関連フラグあり）
    - Response:
      - `instanceID`:
        操作用ID
      - `fileName`:
        実際に読み込まれたファイル名
      - `customData*`:
        カスタムデータ読込時に返却される関連フィールド

- 実運用のイメージ
  1. `ItemListRequest` で取得した `fileName` を指定する。
  2. 位置・サイズ・順序・フェードなどを設定して読み込む。
  3. 後片付けのため `unloadWhenPluginDisconnects=true` を基本にする。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemLoadRequest",
    "data": {
      "fileName": "some_item_name.jpg",
      "positionX": 0,
      "positionY": 0.5,
      "size": 0.33,
      "rotation": 90,
      "fadeTime": 0.5,
      "order": 4,
      "failIfOrderTaken": false,
      "smoothing": 0,
      "censored": false,
      "flipped": false,
      "locked": false,
      "unloadWhenPluginDisconnects": true,
      "customDataBase64": "",
      "customDataAskUserFirst": true,
      "customDataSkipAskingUserIfWhitelisted": true,
      "customDataAskTimer": -1
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemLoadResponse",
    "data": {
      "instanceID": "SomeUniqueItemInstanceId",
      "fileName": "some_item_name.jpg"
    }
  }
  ```

### ItemUnloadRequest

- apiの概要
  - シーンからItemを削除するAPIである。
  - 主要データ:
    - Request:
      - `unloadAllInScene`:
        全削除
      - `unloadAllLoadedByThisPlugin`:
        自プラグイン分削除
      - `allowUnloadingItemsLoadedByUserOrOtherPlugins`:
        許可制御
      - `instanceIDs`:
        削除対象のインスタンスID一覧
      - `fileNames`:
        削除対象のファイル名一覧
    - Response:
      - `unloadedItems[]`:
        実際に削除されたItem

- 実運用のイメージ
  1. 全削除・自プラグイン削除・個別削除の方針を決める。
  2. 必要なID/ファイル名を指定して `ItemUnloadRequest` を送信する。
  3. `unloadedItems[]` を見て削除結果を反映する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemUnloadRequest",
    "data": {
      "unloadAllInScene": false,
      "unloadAllLoadedByThisPlugin": false,
      "allowUnloadingItemsLoadedByUserOrOtherPlugins": true,
      "instanceIDs": [
        "SomeInstanceId"
      ],
      "fileNames": [
        "SomeFileName"
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemUnloadResponse",
    "data": {
      "unloadedItems": [
        {
          "instanceID": "SomeInstanceId",
          "fileName": "SomeFileName"
        }
      ]
    }
  }
  ```

### ItemAnimationControlRequest

- apiの概要
  - Itemのアニメ再生状態や見た目を制御するAPIである。
  - 主要データ:
    - Request:
      - `itemInstanceID`:
        操作対象のItemインスタンスID
      - `framerate`:
        再生フレームレート
      - `frame`:
        現在フレームの指定値
      - `brightness`:
        明るさ倍率
      - `opacity`:
        不透明度
      - `setAutoStopFrames`:
        自動停止フレーム設定を反映するか
      - `autoStopFrames`:
        自動停止するフレーム番号一覧
      - `setAnimationPlayState`:
        再生状態設定を反映するか
      - `animationPlayState`:
        `true` で再生、`false` で停止
    - Response:
      - `frame`:
        現在フレーム
      - `animationPlaying`:
        再生中か

- 実運用のイメージ
  1. 対象 `itemInstanceID` がアニメ対応Itemか確認する。
  2. `framerate`/`frame`/`opacity`/`brightness` を必要分だけ指定して送る。
  3. `frame` と `animationPlaying` を見て再生状態を同期する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemAnimationControlRequest",
    "data": {
      "itemInstanceID": "ItemInstanceId",
      "framerate": 12,
      "frame": 3,
      "brightness": 1,
      "opacity": 1,
      "setAutoStopFrames": true,
      "autoStopFrames": [
        0,
        7,
        26
      ],
      "setAnimationPlayState": true,
      "animationPlayState": true
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemAnimationControlResponse",
    "data": {
      "frame": 3,
      "animationPlaying": true
    }
  }
  ```

### ItemMoveRequest

- apiの概要
  - 複数Itemを一括移動するAPIである。
  - 主要データ:
    - Request:
      - `itemsToMove[]`:
        移動対象Itemごとの設定配列
      - `itemInstanceID`:
        移動対象のItemインスタンスID
      - `timeInSeconds`:
        移動にかける時間
      - `fadeMode`:
        補間方式（`linear` / `easeIn` / `easeOut` など）
      - `positionX`/`positionY`/`rotation`/`size`:
        位置・回転・サイズの目標値
      - `order`:
        描画順の目標値
      - `setFlip`/`flip`:
        反転状態を変更するかと目標値
      - `userCanStop`:
        ユーザー操作で移動を中断可能にするか
    - Response:
      - `movedItems[]`:
        各Itemの移動結果配列
      - `success`:
        そのItemの移動が成功したか
      - `errorID`:
        失敗時のエラーID（成功時は-1）

- 実運用のイメージ
  1. `itemsToMove[]` に対象Itemごとの移動条件を作る。
  2. `timeInSeconds` と `fadeMode` を目的に合わせて設定する。
  3. `movedItems[]` の `success/errorID` で個別に成否判定する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemMoveRequest",
    "data": {
      "itemsToMove": [
        {
          "itemInstanceID": "ItemInstanceId",
          "timeInSeconds": 1,
          "fadeMode": "easeOut",
          "positionX": 0.2,
          "positionY": -0.8,
          "size": 0.6,
          "rotation": 180,
          "order": -1000,
          "setFlip": true,
          "flip": false,
          "userCanStop": true
        }
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemMoveResponse",
    "data": {
      "movedItems": [
        {
          "itemInstanceID": "ItemInstanceId",
          "success": true,
          "errorID": -1
        }
      ]
    }
  }
  ```

### ItemSortRequest

- apiの概要
  - Itemのモデル内部レイヤー挿入位置を設定するAPIである。
  - 主要データ:
    - Request:
      - `itemInstanceID`:
        操作対象のItemインスタンスID
      - `frontOn`:
        モデル前面レイヤーへの配置を有効化するか
      - `backOn`:
        モデル背面レイヤーへの配置を有効化するか
      - `setSplitPoint`:
        前後分割点の指定方法
      - `setFrontOrder`:
        前面側の並び順指定方法
      - `setBackOrder`:
        背面側の並び順指定方法
      - `splitAt`:
        分割点として使うArtMesh IDまたはSpecial ID
      - `withinModelOrderFront`:
        前面側の基準ArtMesh IDまたはSpecial ID
      - `withinModelOrderBack`:
        背面側の基準ArtMesh IDまたはSpecial ID
    - Response:
      - `loadedModelHadRequestedFrontLayer`:
        指定した前面レイヤーがモデル内に存在したか
      - `loadedModelHadRequestedBackLayer`:
        指定した背面レイヤーがモデル内に存在したか

- 実運用のイメージ
  1. 対象 `itemInstanceID` と前後レイヤー方針を決める。
  2. `setFrontOrder`/`setBackOrder`/`setSplitPoint` を指定して送信する。
  3. 返却フラグで指定レイヤーが存在したか確認する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemSortRequest",
    "data": {
      "itemInstanceID": "b616cf51...",
      "frontOn": true,
      "backOn": true,
      "setSplitPoint": "UseArtMeshID",
      "setFrontOrder": "UseArtMeshID",
      "setBackOrder": "UseSpecialID",
      "splitAt": "MyArtMeshIDInItemModel91",
      "withinModelOrderFront": "MyArtMeshIDInMainModel73",
      "withinModelOrderBack": "FullyInBack"
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemSortResponse",
    "data": {
      "itemInstanceID": "b616cf51...",
      "modelLoaded": true,
      "modelID": "d87b771d...",
      "modelName": "Akari",
      "loadedModelHadRequestedFrontLayer": true,
      "loadedModelHadRequestedBackLayer": true
    }
  }
  ```

### ArtMeshSelectionRequest

- apiの概要
  - ユーザーにArtMesh選択UIを表示して選択結果を受け取るAPIである。
  - 主要データ:
    - Request:
      - `requestedArtMeshCount`:
        必要選択数
      - `activeArtMeshes`:
        初期選択
      - `textOverride`:
        表示文言上書き
      - `helpOverride`:
        表示文言上書き
    - Response:
      - `success`:
        `true` なら決定、`false` ならキャンセル
      - `activeArtMeshes`:
        選択結果
      - `inactiveArtMeshes`:
        選択結果

- 実運用のイメージ
  1. 必要選択数と案内文を設定して送信する。
  2. VTS側でユーザー操作が完了するまで応答待ちする。
  3. `success` と `activeArtMeshes` を使って後続処理を実行する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ArtMeshSelectionRequest",
    "data": {
      "textOverride": "This text is shown over the ArtMesh selection list.",
      "helpOverride": "This text is shown when the user presses the ? button.",
      "requestedArtMeshCount": 5,
      "activeArtMeshes": [
        "D_BODY_00",
        "D_ARM_R_05"
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ArtMeshSelectionResponse",
    "data": {
      "success": true,
      "activeArtMeshes": [
        "D_BROW_00",
        "D_EYE_11"
      ],
      "inactiveArtMeshes": [
        "D_EAR_06",
        "D_BODY_00"
      ]
    }
  }
  ```

### ItemPinRequest

- apiの概要
  - Itemをモデル/ArtMeshへピン留めまたは解除するAPIである。
  - 主要データ:
    - Request:
      - `pin`:
        trueで留める
      - `itemInstanceID`:
        操作対象のItemインスタンスID
      - `angleRelativeTo`:
        角度の基準（モデル基準かワールド基準か）
      - `sizeRelativeTo`:
        サイズの基準（モデル基準かワールド基準か）
      - `vertexPinType`:
        頂点指定方式（自動/手動指定）
      - `pinInfo`:
        ピン留め先モデル・ArtMesh・頂点重み情報
    - Response:
      - `isPinned`:
        現在のピン状態
      - `itemInstanceID`:
        対象ItemインスタンスID
      - `itemFileName`:
        対象Itemのファイル名

- 実運用のイメージ
  1. ピン留め対象 `itemInstanceID` と方式（角度/サイズ/頂点種別）を決める。
  2. `pinInfo` を設定して送信し、必要なら再送で位置更新する。
  3. 解除時は `pin=false` のみ送ってアンピンする。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "ItemPinRequest",
    "data": {
      "pin": true,
      "itemInstanceID": "4a241269...",
      "angleRelativeTo": "RelativeToModel",
      "sizeRelativeTo": "RelativeToWorld",
      "vertexPinType": "Provided",
      "pinInfo": {
        "modelID": "d87b771d...",
        "artMeshID": "hair_right_4",
        "angle": 23.938,
        "size": 0.33,
        "vertexID1": 17,
        "vertexID2": 9,
        "vertexID3": 55,
        "vertexWeight1": 0.259,
        "vertexWeight2": 0.685,
        "vertexWeight3": 0.056
      }
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "ItemPinResponse",
    "data": {
      "isPinned": true,
      "itemInstanceID": "4a241269...",
      "itemFileName": "my_test_item_2.png"
    }
  }
  ```

### PostProcessingListRequest

- apiの概要
  - ポストプロセス(VFX)状態と設定一覧を取得するAPIである。
  - 主要データ:
    - Request:
      - `fillPostProcessingPresetsArray`:
        重い配列の取得可否
      - `fillPostProcessingEffectsArray`:
        重い配列の取得可否
      - `effectIDFilter`:
        対象効果絞り込み
    - Response:
      - `postProcessingActive`:
        ポストプロセスが現在有効か
      - `restrictedEffectsAllowed`:
        制限付きエフェクトの利用が許可されているか
      - `activePreset`:
        現在適用中のプリセット名
      - `presetCount` / `activeEffectCount`:
        プリセット総数と現在有効なエフェクト数
      - `postProcessingEffects[]`:
        取得対象となったエフェクト設定一覧
      - `postProcessingPresets[]`:
        利用可能なプリセット名一覧

- 実運用のイメージ
  1. 取得目的に合わせて `fillPostProcessing*` と `effectIDFilter` を設定する。
  2. `postProcessingActive` と `activePreset` を見て現在状態を把握する。
  3. 詳細制御が必要な場合のみ効果一覧を取得して更新対象を決める。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "PostProcessingListRequest",
    "data": {
      "fillPostProcessingPresetsArray": true,
      "fillPostProcessingEffectsArray": true,
      "effectIDFilter": [
        "ASCII",
        "ColorGrading",
        "WeatherEffects",
        "ChromaticAberration"
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "PostProcessingListResponse",
    "data": {
      "postProcessingSupported": true,
      "postProcessingActive": true,
      "canSendPostProcessingUpdateRequestRightNow": true,
      "restrictedEffectsAllowed": false,
      "presetIsActive": true,
      "activePreset": "some_effects_preset_3",
      "presetCount": 70,
      "activeEffectCount": 5,
      "effectCountBeforeFilter": 29,
      "configCountBeforeFilter": 258,
      "effectCountAfterFilter": 4,
      "configCountAfterFilter": 31,
      "postProcessingEffects": [],
      "postProcessingPresets": [
        "My Cool Preset",
        "some_effects_preset_3"
      ]
    }
  }
  ```

### PostProcessingUpdateRequest

- apiの概要
  - ポストプロセス設定を更新するAPIである。
  - 主要データ:
    - Request:
      - `postProcessingOn`:
        ポストプロセス機能を有効化するか
      - `setPostProcessingPreset`:
        プリセット指定
      - `presetToSet`:
        適用するプリセット名
      - `setPostProcessingValues`:
        個別設定
      - `postProcessingValues`:
        個別に更新する設定値配列
      - `postProcessingFadeTime`:
        設定反映に使うフェード時間（秒）
      - `usingRestrictedEffects`:
        制限系
      - `randomizeAll`:
        全設定をランダム化するか
    - Response:
      - `postProcessingActive`:
        反映後の有効状態
      - `presetIsActive`:
        プリセット適用状態か
      - `activePreset`:
        現在適用中のプリセット名
      - `activeEffectCount`:
        有効なエフェクト数

- 実運用のイメージ
  1. プリセット適用か個別値更新かを選び、同時指定しない。
  2. `postProcessingFadeTime` と制限項目を設定して送信する。
  3. `activeEffectCount` と有効状態を確認し、必要なら再調整する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "PostProcessingUpdateRequest",
    "data": {
      "postProcessingOn": true,
      "setPostProcessingPreset": false,
      "setPostProcessingValues": true,
      "presetToSet": "",
      "postProcessingFadeTime": 1.3,
      "setAllOtherValuesToDefault": true,
      "usingRestrictedEffects": false,
      "randomizeAll": false,
      "randomizeAllChaosLevel": 0.0,
      "postProcessingValues": [
        {
          "configID": "Backlight_Strength",
          "configValue": "0.8"
        },
        {
          "configID": "Bloom_Strength",
          "configValue": "1.0"
        }
      ]
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "PostProcessingUpdateResponse",
    "data": {
      "postProcessingActive": true,
      "presetIsActive": false,
      "activePreset": "",
      "activeEffectCount": 2
    }
  }
  ```

## イベントの購読(サブスクライブ)と購読解除(アンサブスクライブ)
以前のAPIバージョンでは、読み込まれているモデルやアイテムなどの情報を、プラグイン側が繰り返しポーリング(定期的に問い合わせ)して取得する必要があった。
現在はVTube Studioがイベントの購読に対応しており、プラグインに関係する何かが起きたときに、VTube Studioから自動的にメッセージが送られてくるようになった。
イベントには、たとえば次のようなものがある。

- アイテムが読み込まれたときの通知
- トラッキングが失われた／復帰したときの通知
- モデルがクリックされたときの通知

取得元URL:
https://github.com/DenchiSoft/VTubeStudio/tree/master/Events

### EventSubscriptionRequest

- apiの概要
  - イベント購読/解除を行うAPIである。
  - 主要データ:
    - Request:
      - `eventName`:
        対象イベント名
      - `subscribe`:
        購読=true/解除=false
      - `config`:
        イベント固有設定
    - Response:
      - `subscribed`:
        現在購読状態
      - `eventName`:
        対象イベント

- 実運用のイメージ
  1. 受け取りたい `eventName` を決め、必要なら `config` を設定して購読する。
  2. 受信イベントをアプリ側キューへ流し、UIや制御ロジックを更新する。
  3. 不要になったイベントは `subscribe=false` で解除する。

- Request例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "requestID": "SomeID",
    "messageType": "EventSubscriptionRequest",
    "data": {
      "eventName": "ModelLoadedEvent",
      "subscribe": true,
      "config": {}
    }
  }
  ```

- Response例
  ```json
  {
    "apiName": "VTubeStudioPublicAPI",
    "apiVersion": "1.0",
    "timestamp": 1625405710728,
    "requestID": "SomeID",
    "messageType": "EventSubscriptionResponse",
    "data": {
      "subscribed": true,
      "eventName": "ModelLoadedEvent"
    }
  }
  ```
