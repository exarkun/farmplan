jQuery.noConflict();
jQuery(document).ready(function() {
    /* Get Underscore.js to give up the global name _ */
    var underscore = _.noConflict();

    function template(id) {
        return underscore.template(jQuery(id).html());
    }

    var Crop = Backbone.Model.extend({
        urlRoot: "../api/crops",
        defaults: {
            id: null,
            name: "",
            description: "",
            picture: "",
            yield_lbs_per_bed_foot: "",
            rows_per_bed: "",
            in_row_spacing: "",
            row_feet_per_oz_seed: "",
            harvest_weeks: ""}});

    var CropPlan = Backbone.Collection.extend({
        model: Crop,
        url: "../api/crops"});

    var CropPlanView = Backbone.View.extend({
        tagName: "ul",

        initialize: function initialize() {
            var self = this;
            this.model.bind("reset", this.render, this);
            this.model.bind("add", function addCrop(crop) {
                jQuery(self.el).append(new CropPlanItemView({model: crop}).render().el);
            });
        },

        render: function renderCropPlanView() {
            underscore.each(this.model.models, function renderOneCrop(crop) {
                jQuery(this.el).append(new CropPlanItemView({model: crop}).render().el);
            }, this);
            return this;
        }});

    var CropPlanItemView = Backbone.View.extend({
        tagName: "li",
        template: template("#template-crop-plan-item"),

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

    var CropView = Backbone.View.extend({
        template: template("#template-crop-details"),

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
            var attributes = {};
            for (var field in this.model.defaults) {
                if (field == "id") {
                    continue;
                }
                attributes[field] = jQuery("#" + field).val();
            }
            /* TODO Check for success or failure on this - and on failure,
             * revert view changes? */
            this.model.set(attributes);

            /* Let the user know some network operation is happening */
            var status = jQuery("#status-communicating");
            status.css("display", "block");

            var options = {
                wait: true,
                success: function() {
                    status.css("display", "none");
                },
                error: function(model, xhr, options) {
                    status.css("display", "none");
                    alert("Problem synchronizing with server; values not saved.");
                }};

            if (this.model.isNew()) {
                app.cropPlan.create(this.model, options);
            } else {
                this.model.save(null, null, options);
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


    var HeaderView = Backbone.View.extend({
        template: underscore.template(jQuery('#template-header').html()),

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
});
