```
<?xml version="1.0" encoding="UTF-8"?>
<bpmn2:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:activiti="http://activiti.org/bpmn" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsd="http://www.w3.org/2001/XMLSchema" id="sample-diagram" targetNamespace="http://www.activiti.org/bpmn" xsi:schemaLocation="http://www.omg.org/spec/BPMN/20100524/MODEL BPMN20.xsd">
  <bpmn2:process id="Process_1" isExecutable="true">
    <bpmn2:startEvent id="StartEvent_1" />
    <bpmn2:sequenceFlow id="Flow_1cluix9" sourceRef="StartEvent_1" targetRef="Activity_035m2a0" />
    <bpmn2:exclusiveGateway id="Gateway_0alg9q8" default="Flow_0m27er5" />
    <bpmn2:serviceTask id="Activity_035m2a0" name="rule拒绝" activiti:class="com.ecreditpal.earring.service.workflow.CheckpointServiceTask">
      <bpmn2:extensionElements>
        <activiti:field name="checkpoint">
          <activiti:string>rule拒绝</activiti:string>
        </activiti:field>
      </bpmn2:extensionElements>
    </bpmn2:serviceTask>
    <bpmn2:sequenceFlow id="Flow_00za1sj" sourceRef="Activity_035m2a0" targetRef="Gateway_0alg9q8" />
    <bpmn2:endEvent id="Event_1yqks82" name="拒绝" />
    <bpmn2:sequenceFlow id="Flow_1jqqi3w" sourceRef="Gateway_0alg9q8" targetRef="Event_1yqks82">
      <bpmn2:conditionExpression xsi:type="bpmn2:tFormalExpression">${rule拒绝== true}</bpmn2:conditionExpression>
    </bpmn2:sequenceFlow>
    <bpmn2:sequenceFlow id="Flow_0m27er5" sourceRef="Gateway_0alg9q8" targetRef="Activity_15vuuki" />
    <bpmn2:exclusiveGateway id="Gateway_05eyprw" default="Flow_12fs6u2" />
    <bpmn2:serviceTask id="Activity_15vuuki" name="rule通过" activiti:class="com.ecreditpal.earring.service.workflow.CheckpointServiceTask">
      <bpmn2:extensionElements>
        <activiti:field name="checkpoint">
          <activiti:string>rule通过</activiti:string>
        </activiti:field>
      </bpmn2:extensionElements>
    </bpmn2:serviceTask>
    <bpmn2:sequenceFlow id="Flow_17yb10c" sourceRef="Activity_15vuuki" targetRef="Gateway_05eyprw" />
    <bpmn2:endEvent id="Event_0c6yfqg" name="拒绝" />
    <bpmn2:endEvent id="Event_1gytoy8" name="通过" />
    <bpmn2:sequenceFlow id="Flow_09jz2ea" sourceRef="Gateway_05eyprw" targetRef="Event_0c6yfqg">
      <bpmn2:conditionExpression xsi:type="bpmn2:tFormalExpression">${rule通过==false}</bpmn2:conditionExpression>
    </bpmn2:sequenceFlow>
    <bpmn2:sequenceFlow id="Flow_12fs6u2" sourceRef="Gateway_05eyprw" targetRef="Event_1gytoy8" />
  </bpmn2:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_Process_1">
    <bpmndi:BPMNPlane id="BPMNPlane_Process_1" bpmnElement="Process_1">
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_12fs6u2" bpmnElement="Flow_12fs6u2">
        <di:waypoint x="1135" y="250" />
        <di:waypoint x="1262" y="250" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_09jz2ea" bpmnElement="Flow_09jz2ea">
        <di:waypoint x="1110" y="275" />
        <di:waypoint x="1110" y="329" />
        <di:waypoint x="1120" y="329" />
        <di:waypoint x="1120" y="382" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_17yb10c" bpmnElement="Flow_17yb10c">
        <di:waypoint x="970" y="250" />
        <di:waypoint x="1085" y="250" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_0m27er5" bpmnElement="Flow_0m27er5">
        <di:waypoint x="765" y="258" />
        <di:waypoint x="818" y="258" />
        <di:waypoint x="818" y="250" />
        <di:waypoint x="870" y="250" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_1jqqi3w" bpmnElement="Flow_1jqqi3w">
        <di:waypoint x="740" y="283" />
        <di:waypoint x="740" y="382" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_00za1sj" bpmnElement="Flow_00za1sj">
        <di:waypoint x="610" y="258" />
        <di:waypoint x="715" y="258" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="BPMNEdge_Flow_1cluix9" bpmnElement="Flow_1cluix9">
        <di:waypoint x="448" y="258" />
        <di:waypoint x="510" y="258" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="BPMNShape_StartEvent_1" bpmnElement="StartEvent_1">
        <dc:Bounds x="412" y="240" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Gateway_0alg9q8" bpmnElement="Gateway_0alg9q8" isMarkerVisible="true">
        <dc:Bounds x="715" y="233" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Activity_035m2a0" bpmnElement="Activity_035m2a0">
        <dc:Bounds x="510" y="218" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Event_1yqks82" bpmnElement="Event_1yqks82">
        <dc:Bounds x="722" y="382" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Gateway_05eyprw" bpmnElement="Gateway_05eyprw" isMarkerVisible="true">
        <dc:Bounds x="1085" y="225" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Activity_15vuuki" bpmnElement="Activity_15vuuki">
        <dc:Bounds x="870" y="210" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Event_0c6yfqg" bpmnElement="Event_0c6yfqg">
        <dc:Bounds x="1102" y="382" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="BPMNShape_Event_1gytoy8" bpmnElement="Event_1gytoy8">
        <dc:Bounds x="1262" y="232" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn2:definitions>


```

