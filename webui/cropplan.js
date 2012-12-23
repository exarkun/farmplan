jQuery.noConflict();

window.Crop = Backbone.Model.extend({
    urlRoot: "../api/crops",
    defaults: {
        id: null,
        name: "",
        description: "",
        picture: ""}});

window.CropPlan = Backbone.Collection.extend({
    model: window.Crop,
    url: "../api/crops"});

window.CropPlanView = Backbone.View.extend({
    tagName: "ul",

    initialize: function initialize() {
        this.model.bind("reset", this.render, this);
        this.model.bind("add", function addCrop(crop) {
            jQuery(self.el).append(new CropPlanItemView({model: crop}).render().el);
        });
    },

    render: function renderCropPlanView() {
        /* XXX _? */
        _.each(this.model.models, function renderOneCrop(crop) {
            jQuery(this.el).append(new CropPlanItemView({model: crop}).render().el);
        }, this);
        return this;
    }});

var t = jQuery("#template-crop-plan-item");
var h = t.html();
/* XXX _? */
var tt = _.template(h);

window.CropPlanItemView = Backbone.View.extend({
    tagName: "li",
    template: tt,

    initialize: function initializeCropPlanItemView() {
        this.model.bind("change", this.render, this);
        this.model.bind("destroy", this.close, this);
    },

    render: function renderCropPlanItemView() {
        jQuery(this.el).html(this.template(this.model.toJSON()));
        return this;
    },

    close: function closeCropPlanItemView() {
        jQuery(this.el).unbind();
        jQuery(this.el).remove();
    }});

window.CropView = Backbone.View.extend({
    /* XXX _? */
    template: _.template(jQuery("#template-crop-details").html()),

    initialize: function initializeCropView () {
        this.model.bind("change", this.render, this);
    },

    render: function renderCropView() {
        jQuery(this.el).html(this.template(this.model.toJSON()));
        return this;
    },

    events:{
        "click .save": "saveCrop",
        "click .delete": "deleteCrop"
    },

    saveCrop: function saveCrop() {
        this.model.set({
            name: jQuery('#name').val(),
            description: jQuery('#description').val()
        });
        if (this.model.isNew()) {
            app.cropPlan.create(this.model);
        } else {
            this.model.save();
        }
        return false;
    },

    deleteCrop: function deleteCrop() {
        this.model.destroy({
            success: function deleteSuccess () {
                alert('Crop deleted');
                window.history.back();
            }
        });
        return false;
    },

    close: function closeCrop() {
        jQuery(this.el).unbind();
        jQuery(this.el).empty();
    }});


window.HeaderView = Backbone.View.extend({
    template: _.template(jQuery('#template-header').html()),

    initialize: function initializeHeader() {
        this.render();
    },

    render: function renderHeader(eventName) {
        jQuery(this.el).html(this.template());
        return this;
    },

    events: {
        "click .new": "newCrop"
    },

    newCrop: function newCrop(event) {
        if (app.cropView) {
            app.cropView.close();
        }
        app.cropView = new CropView({model: new Crop()});
        jQuery('#content').html(app.cropView.render().el);
        return false;
    }});


var AppRouter = Backbone.Router.extend({
    routes: {
        "": "list",
        "crops/:id": "crop-details"},

    initialize: function initializeRouter() {
        jQuery('#header').html(new HeaderView().render().el);
    },

    list: function list() {
        this.cropPlan = new CropPlan();
        this.cropPlanView = new CropPlanView({model: this.cropPlan});
        this.cropPlan.fetch();
        jQuery('#sidebar').html(this.cropPlanView.render().el);
    },

    "crop-details": function crop_details(id) {
        this.crop = this.cropPlan.get(id);
        this.cropView = new CropView({model: this.crop});
        jQuery('#content').html(this.cropView.render().el);
    }});

var app = new AppRouter();
Backbone.history.start();
