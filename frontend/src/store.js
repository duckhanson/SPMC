import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

// 定義一個新的 Vue Store
const store = new Vuex.Store({
    state: {
        container_infos: [],
        box_infos:[],
        render_infos:[],
        render_loading_status:false,
    },
    mutations: {
        // 將state設定為參數
        MUTATE_CONTAINER_INFO: (state, new_container_infos) => {
            state.container_infos = new_container_infos;
        },
        MUTATE_BOX_INFO:(state, new_box_infos)=>{
            state.box_infos=new_box_infos;
        },
        MUTATE_APPEND_CONTAINER_INFO(state, container_info_to_be_appended){
            state.container_infos=[...state.container_infos, ...container_info_to_be_appended]
        },
        MUTATE_APPEND_BOX_INFO(state, box_info_to_be_append){
            state.box_infos=[...state.box_infos, ...box_info_to_be_append]
        },
        MUTATE_DELETE_CONTAINER_WITH_UUID(state, uuid){

            //initial value is empty array
            state.container_infos=state.container_infos.reduce((new_array, current_val)=>{
                current_val.ID!==uuid && new_array.push(current_val);
                return new_array;
            },[])
        },
        MUTATE_DELETE_BOX_WITH_UUID(state, uuid){

            //initial value is empty array
            console.log(uuid)
            state.box_infos=state.box_infos.reduce((new_array, current_val)=>{
                current_val.ID!==uuid && new_array.push(current_val);
                return new_array;
            },[])
        },
        MUTATE_RENDER_DATA(state, new_render_infos){
            state.render_infos=new_render_infos;
        },
        MUTATE_RENDER_LOADING_STATUS(state, new_staus){
            state.render_loading_status=new_staus;
        }
    },//end mutation
    actions: {
        loadContainerInfos: (context, container_infos) => {
            context.commit('MUTATE_CONTAINER_INFO', container_infos);
        },//end loadContainerInfos
        loadBoxInfos:(context, box_infos)=>{
            context.commit('MUTATE_BOX_INFO', box_infos);
        },
        appendContainerInfos:(context, container_info)=>{
            context.commit("MUTATE_APPEND_CONTAINER_INFO", container_info)
        },
        appendBoxInfos:(context, box_info)=>{
            context.commit("MUTATE_APPEND_BOX_INFO", box_info)
        },
        deleteContainer_infosItemWithUUID:(context, uuid)=>{
            context.commit("MUTATE_DELETE_CONTAINER_WITH_UUID", uuid)
        },
        deleteBox_infosItemWithUUID:(context, uuid) =>{
            context.commit("MUTATE_DELETE_BOX_WITH_UUID", uuid)
        },
        loadRenderInfos:(context, render_infos)=>{
            context.commit("MUTATE_RENDER_DATA", render_infos)
        },
        setRenderLoadingStatus:(context, new_status)=>{
            context.commit("MUTATE_RENDER_LOADING_STATUS", new_status);
            console.log("render status become"+new_status)
        }
    },//end actions
    getters:{
        getContainerInfos:state=>{
            return state.container_infos
        }
    }
    })//end store
export default store;